#!/usr/bin/env python3
"""只读地打印本机的预算读数，供人工核对。不加载模型、不起作业、不写文件。

末尾那一节（--no-resident-probe 可关）是唯一的例外，且例外得有分寸：它在一个**子
进程**里真实占住一块匿名内存，再让 arbiter 走一遍 `_backfill_resident`，把量到的
`bytes_resident` 和子进程实际占住的量并排打出来。不这样做就没有任何真机证据说明
R-budget-12 的那个数字是对的——手搓一个 `bytes_resident=30 GiB` 喂给 `fits` 验的是
`_unallocated` 的算术，不是「回填能不能量出 30 GiB」。它仍然不加载模型、不起作业、
不写文件，占用的内存在本脚本退出前一定归还。
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from desk.arbiter.core import RESIDENT_MIN_BYTES, Arbiter
from desk.arbiter.memory import MemoryReader
from desk.budget.budget import Budget, Workload, fits
from desk.budget.store import Measurements
from desk.media.memory_estimate import estimate_bytes

GIB = 1024 ** 3

PROBE_ALLOC_BYTES = 16 * GIB        # 子进程真实占住这么多：远高于 RESIDENT_MIN_BYTES
PROBE_NEEDED_BYTES = 24 * GIB       # 探针 workload 声称要这么多（回填会夹在这以内）
PROBE_HEADROOM_BYTES = 32 * GIB     # 可用低于这个数就不探，免得给正在用的机器添压力

# 子进程：占住 PROBE_ALLOC_BYTES 真实内存，报 READY，然后堵在 stdin 上等父进程收工。
# 不碰文件、不碰网络。填的是随机字节而不是零页：macOS 的内存压缩器按页压，
# 一页零字节几乎不占物理内存，用 bytearray(n) 探出来的降幅会只有真实占用的一半。
PROBE_CHILD = """
import os, sys
size = int(sys.argv[1])
block = os.urandom(1 << 20)
buf = block * (size >> 20)
print("READY", flush=True)
sys.stdin.read(1)
print(len(buf))
"""


def print_readback(budget, snap) -> None:
    print(f"{'模型':34} {'权重GB':>6} {'窗口':>8} {'额度':>10} {'压缩点':>10}  来源")
    print("-" * 82)
    for directory in sorted((Path.home() / "LocalModelDesk/llms").glob("*/*/")):
        config_path = directory / "config.json"
        if not config_path.is_file():
            continue
        weights_gb = sum(f.stat().st_size for f in directory.glob("*.safetensors")) / 1e9
        chat = budget.for_chat(directory.name, json.loads(config_path.read_text()), weights_gb)
        print(f"{directory.name[:34]:34} {weights_gb:>6.0f} {str(chat.window or '—'):>8}"
              f" {chat.token_limit:>10,} {chat.compact_at:>10,}  {chat.source}")

    print("\n共存判定（驻留一个 30 GB 模型、其权重已分配时，还能不能开视频）：")
    resident = Workload("llm", "resident", int(60 * GIB), "measured", bytes_resident=int(30 * GIB))
    video = Workload("video", None, estimate_bytes("video", {}), "predicted")
    verdict = fits([resident, video], snap.available_bytes)
    print(f"  需要 {verdict.needed_bytes / GIB:.1f} GiB · 可用 {verdict.available_bytes / GIB:.1f} GiB"
          f" · 依据 {verdict.source} ⇒ {'装得下' if verdict.ok else '装不下'}")


def probe_backfill(snap) -> int:
    """真机走一遍回填链路：授予 → 子进程真占内存 → 读快照回填 → 打印量到的值。"""
    print("\n回填链路实测（R-budget-12：bytes_resident 由实测得出，不由估算）：")
    if snap.available_bytes < PROBE_HEADROOM_BYTES:
        print(f"  跳过：可用只有 {snap.available_bytes / GIB:.1f} GiB，低于 "
              f"{PROBE_HEADROOM_BYTES / GIB:.0f} GiB 的探测门槛，不给这台机器添压力。")
        return 0

    # 真 MemoryReader、真 Arbiter、真 _backfill_resident；只有 cost() 是桩，因为
    # 这条链路要验的是「降幅能不能被量出来」，不是「一件作业要多少内存」。
    budget = SimpleNamespace(cost=lambda kind, **kw: Workload(
        kind, kw.get("key"), PROBE_NEEDED_BYTES, "measured"))
    arbiter = Arbiter(
        llm_port=0, memory=MemoryReader(), budget=budget,
        # 探针绝不该走到让出分支（只有一件持有者）；万一走到，也不许去杀任何端口。
        reaper=lambda port, **kw: SimpleNamespace(
            ok=False, port=port, killed_pids=[], error="probe never reaps"),
    )

    granted = arbiter.acquire_heavy("video", "resident-probe", params={}, key="h3")
    if not granted.get("ok"):
        print(f"  跳过：授予被拒（{granted.get('reason')}）。")
        return 1
    token = granted["token"]

    def resident_now() -> int:
        # 私有字段：arbiter 没有公开「这件重活量到多少」的读口，而这正是要核对的数。
        return next(iter(arbiter._workloads.values())).bytes_resident

    print(f"  基线可用 {arbiter._grant_baseline[token] / GIB:.2f} GiB"
          f" · 授予时立刻回填得到 {resident_now() / GIB:.2f} GiB"
          f"（噪声下限 {RESIDENT_MIN_BYTES / GIB:.0f} GiB 之下都记 0）")

    child = subprocess.Popen(
        [sys.executable, "-c", PROBE_CHILD, str(PROBE_ALLOC_BYTES)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        if (child.stdout.readline() or "").strip() != "READY":
            print("  跳过：子进程没能占住内存。")
            return 1
        time.sleep(1.5)                       # 让 vm_stat 的计数跟上
        rss = child_rss_bytes(child.pid)
        arbiter.desk_state()                  # 读快照 ⇒ 顺带回填
        measured = resident_now()
    finally:
        child.stdin.close()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
        arbiter.release_heavy(token)

    ratio = measured / rss if rss else 0.0
    print(f"  子进程实占 {rss / GIB:.2f} GiB（ps rss）⇒ 回填量到 {measured / GIB:.2f} GiB"
          f"，占 {ratio * 100:.0f}%")
    print("  注：占比明显小于 100% 是 available_bytes 的口径使然，不是回填算错了。"
          "本机实测：子进程占 12 GiB 时 Pages free 降 12.5 GiB，但 Pages inactive 同时涨 5.8 GiB，"
          "而 inactive 也算在 free+inactive+purgeable+speculative 里，于是净降幅只有约 6 GiB。"
          "换句话说 bytes_resident 系统性地偏小——偏小的方向是保守的："
          "fits 多扣、plan 少算回收，都不会因此放行装不下的作业。")
    # 判据只卡「方向对、量级对、上界对」这三件真的成立的事，不假装能对上 100%。
    if RESIDENT_MIN_BYTES <= measured <= rss:
        print("  ⇒ 回填链路成立：量到的是一个真实的、有正确符号且不超过实占的降幅。")
        return 0
    print("  ⇒ 不成立：量到的值越界（不在 [噪声下限, 实占] 之间），请看上面的数字。")
    return 1


def child_rss_bytes(pid: int) -> int:
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)],
                         capture_output=True, text=True).stdout.strip()
    return int(out) * 1024 if out else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-resident-probe", action="store_true",
                        help="不跑回填链路实测（该节会在子进程里临时占用内存）")
    args = parser.parse_args()

    snap = MemoryReader().snapshot()
    print(f"本机：总 {snap.total_bytes / GIB:.0f} GiB · 可用 {snap.available_bytes / GIB:.0f} GiB"
          f" · 压力 {snap.pressure}\n")
    budget = Budget(measurements=Measurements(), memory_reader=MemoryReader(),
                    media_estimate=estimate_bytes, now=lambda: 0.0)
    print_readback(budget, snap)
    if args.no_resident_probe:
        return 0
    return probe_backfill(snap)


if __name__ == "__main__":
    raise SystemExit(main())
