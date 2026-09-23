"""skill 的门面：两个根在哪、扫出来是什么。

不缓存扫描结果：没有文件监听（R-skill-09），缓存会让「重新扫描」按钮变成假的。
"""
from __future__ import annotations

import io
import tarfile
import unicodedata
import urllib.parse       # 必须显式导入：import urllib.request 不保证 urllib.parse 可用，
import urllib.request     # 而单测注入了 fetch、碰不到这一行——正是「单元绿、真机坏」的形状
from pathlib import Path

from .install import InstallError, discard as _discard, land, stage_from_url, sweep_stale_staging
from .store import SkillStore

_TARBALL = "https://codeload.github.com/{owner}/{repo}/tar/refs/heads/{branch}"

# skill 是文本：这三个上限已经比任何真实的 skill 仓库宽出一个数量级，只用来挡住
# 「粘一个链接就把内存或者时间耗光」——本产品的立身之本是资源管理，不能栽在一次没设防
# 的下载或解压上（R-budget，见 2026-09-23 修复轮 1 finding 7、修复轮 2 finding 4）。
_MAX_TARBALL_BYTES = 20 * 1024 * 1024              # 20 MB：整个仓库下载（压缩后）的上限
_MAX_MEMBER_BYTES = 2 * 1024 * 1024                # 2 MB：单个 .md 文件（解压后）的上限
_MAX_TOTAL_DECOMPRESSED_BYTES = 50 * 1024 * 1024   # 50 MB：解压总量上限——压缩包本身不大，
                                                    # 解压出来的内容（不管收不收）可能是炸弹


def _fetch_github(url: str) -> dict[str, str]:
    """把一个 GitHub 仓库 URL 取成 {文件名: 文本}，只收顶层的 `.md`。

    不执行、不解压到磁盘：直接在内存里读 tar 成员，只认顶层 `.md`，别的一概不看
    （R-skill-01/11）。成员名带路径分隔符的跳过——不跟进子目录，也就不可能被
    `../` 写出去。

    大小写只差一个字母的两个成员名（比如 `SKILL.md` 与 `skill.md`）在开发这台设备的
    默认大小写不敏感文件系统上会写到同一个路径——先落盘的那份「赢」，而预览给用户看的
    是另一份。这不是这份代码能悄悄挑一个赢家的问题：用户批准的文本和最终生效的文本
    必须是同一份，所以整个仓库直接拒收（2026-09-23 修复轮 1 finding 1）。

    `casefold()`本身不做 Unicode 规范化：NFC 的 `café.md`（é 是一个码点）和 NFD 的
    `café.md`（e 加一个组合重音符，两个码点）是两个不同的 Python 字符串、casefold
    之后也不同，但 APFS 认为是同一个路径——所以比较之前先 `unicodedata.normalize("NFC",
    ...)`，比的是文件系统会认成同一个路径的那个形式，不是 Python 字符串本身
    （2026-09-23 修复轮 2 finding 1）。

    `tar.getmembers()`会在返回前解压整份归档来枚举所有成员头；改用 `for member in tar`
    逐个取成员，边取边把见到的（不管收不收）decompressed size 累加起来，一超过总量上限
    就地放弃——压缩包本身不大不代表解压出来的东西不大，这条防线管的是解压这段时间，
    不是下载那段流量（2026-09-23 修复轮 2 finding 4）。
    """
    parts = [p for p in urllib.parse.urlparse(url).path.split("/") if p]
    if len(parts) < 2:
        raise ValueError("不是一个仓库地址，形如 https://github.com/<owner>/<repo>")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    last = None
    blob = b""
    for branch in ("main", "master"):
        try:
            with urllib.request.urlopen(
                    _TARBALL.format(owner=owner, repo=repo, branch=branch), timeout=30) as resp:
                blob = resp.read(_MAX_TARBALL_BYTES + 1)
            break
        except Exception as exc:                  # 两个分支都试完才算失败
            last = exc
    else:
        raise ValueError(f"取不到仓库内容：{last}")

    if len(blob) > _MAX_TARBALL_BYTES:
        raise ValueError(
            f"仓库太大：超过 {_MAX_TARBALL_BYTES // (1024 * 1024)} MB 的下载上限"
            "（skill 应该是纯文本，不该这么大）")

    files: dict[str, str] = {}
    seen_casefold: dict[str, str] = {}
    total_decompressed = 0
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        for member in tar:                       # 流式取成员，不像 getmembers() 那样先
                                                   # 解压整份归档（finding 4）
            total_decompressed += member.size
            if total_decompressed > _MAX_TOTAL_DECOMPRESSED_BYTES:
                raise ValueError(
                    f"仓库解压后的内容超过 {_MAX_TOTAL_DECOMPRESSED_BYTES // (1024 * 1024)} "
                    "MB 的上限（压缩包不大不代表解压出来的东西不大）")
            # tarball 的成员都带一层 "<repo>-<branch>/" 前缀，剥掉之后只收顶层 .md
            name = member.name.split("/", 1)[-1] if "/" in member.name else ""
            if not member.isfile() or "/" in name or not name.endswith(".md"):
                continue
            if member.size > _MAX_MEMBER_BYTES:
                raise ValueError(
                    f"{name} 超过单文件 {_MAX_MEMBER_BYTES // (1024 * 1024)} MB 的上限"
                    "（skill 应该是纯文本，不该这么大）")
            folded = unicodedata.normalize("NFC", name).casefold()
            if folded in seen_casefold and seen_casefold[folded] != name:
                raise ValueError(
                    f"{seen_casefold[folded]} 和 {name} 只差大小写或 Unicode 规范化：装到这台"
                    "设备上会写到同一个文件，没法确定该留哪个——整个仓库不装")
            seen_casefold[folded] = name
            files[name] = tar.extractfile(member).read().decode("utf-8", errors="replace")
    return files


class SkillsService:
    def __init__(self, roots):
        self._roots = roots
        # 只在这一刻扫：SkillsService 在 runtime.py 里于 app.start_background() 之前
        # 构造——这是唯一能保证「不可能有 preview 正在写」的时刻，HTTP 服务器还没
        # 开始接受请求（2026-09-23 finding 3，理由见 install.sweep_stale_staging）。
        sweep_stale_staging(self._staging_root())

    def _store(self) -> SkillStore:
        # 自带的那批落在 resources_root/desk/skills/bundled：`build-app.sh:49` 已经把整个
        # `desk/` rsync 进 `Resources/desk/`，所以这条路径在开发模式（resources_root = 仓库根）
        # 与 bundle 模式下都成立，**不需要给构建脚本加一步**。少一步就少一类
        # 「开发机全绿、装进 app 没有」的故障。
        return SkillStore(Path(self._roots.resources_root) / "desk" / "skills" / "bundled",
                          Path(self._roots.models_root) / "skills")

    def list_skills(self) -> dict:
        return {"skills": self._store().scan()}

    def rescan(self) -> dict:
        return self.list_skills()

    def _staging_root(self) -> Path:
        return Path(self._roots.models_root) / "skills" / ".staging"

    def preview_install(self, url: str) -> dict:
        if not isinstance(url, str) or not url.strip():
            raise InstallError("请给一个仓库地址")
        return stage_from_url(url, self._staging_root(), _fetch_github)

    def confirm_install(self, staging_id: str) -> dict:
        # **只落盘，不启用**（R-skill-11）：装和用是两个动作。这里绝不碰任何会话的
        # skills 字段——用户得自己去芯片里点一下。
        name = land(staging_id, self._staging_root(), Path(self._roots.models_root) / "skills")
        return {"installed": name, "enabled": False}

    def discard_install(self, staging_id: str) -> dict:
        _discard(staging_id, self._staging_root())
        return {"discarded": staging_id}
