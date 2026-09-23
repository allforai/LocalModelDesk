"""从 URL 装一个 skill：先看全文，全成功才落盘，任何中断清掉暂存（R-skill-11/17）。

`fetch` 注入进来，所以这一层不联网也能完整测试；生产里由 service 传入真正的抓取实现。

只落 `SKILL.md` 与 `.md` 附件：台面不执行脚本与二进制（R-skill-01），把它们留在磁盘上
只会让人以为它会执行。

`<models_root>/skills/` 下不允许出现「装了一半」的目录：它会被扫描发现、被列成坏 skill，
而用户根本没同意装它。
"""
from __future__ import annotations

import re
import shutil
import threading
import uuid
from pathlib import Path

from .parse import split_skill


class InstallError(Exception):
    pass


def _clear(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


_STAGING_ID = re.compile(r"^[0-9a-f]{32}$")


def _validate_staging_id(staging_id) -> None:
    """`staging_id` 只可能是 `stage_from_url` 自己生成的 `uuid4().hex`——32 位小写
    十六进制字符。它从 HTTP 请求体一路传进来，落地之前从来没被校验过就直接拼进
    路径：`discard` 曾经因此把 `"../../llms"` 当成 staging_id，删掉了整个模型库
    （2026-09-23 finding 1）。

    按形状拒绝比按「../」这种黑名单更彻底：没有一种把 `..` 编码成 32 位十六进制
    字符串的写法，这条校验从根上堵死任何路径穿越，不管穿越用的是哪种编码。
    """
    if not isinstance(staging_id, str) or not _STAGING_ID.fullmatch(staging_id):
        raise InstallError(
            f"staging_id 不合法：必须是 32 位小写十六进制字符，收到的是 {staging_id!r}")


def _validate_skill_name(name: str) -> None:
    """`name` 是要落盘成一层目录名的字符串，不是随便的文本。落盘时从来没被校验过就
    直接拼进路径：声明 `name: ../../escaped` 能装到 `<models_root>/skills/` 之外，
    声明 `name: /abs/path/pwned` 能写到 app 能写的任何地方（pathlib 里
    `Path(...) / 绝对路径` 直接丢弃左边）（2026-09-23 finding 2）。

    允许什么由这里一次性定下来：不含路径分隔符、不以 `.` 开头的任意非空名字——
    含中文在内，自带的三个 skill 本身就用中文做目录名（`译成中文`、`代码审查`、
    `写得清楚些`），「只许 ASCII」这种更严的规则会误伤它们。点开头单独给一条
    消息：`.hidden` 会「装成功」，但扫描器把点开头的目录当成 `.staging` 这类
    临时目录跳过，装了也永远列不出来，比直接拒绝更糟——而且这条顺带堵死了
    `..`（本身就是点开头）这个不含斜杠、却能让 `target` 解析到 `user_root` 上一级
    的名字。
    """
    if name.startswith("."):
        raise InstallError(
            f"skill 的 name 不能以 . 开头（{name!r}）：点开头的目录会被扫描器当成"
            "安装用的临时目录跳过，装了也永远看不见，等于白装")
    if "/" in name or "\\" in name:
        raise InstallError(
            f"skill 的 name 不能包含 / 或 \\（{name!r}）：name 要落盘成一层目录名，"
            "不是一段路径")


def sweep_stale_staging(staging_root: Path) -> None:
    """清掉 `.staging` 下所有暂存目录：用户退出 app 时，没 install 也没 discard 的
    预览就这样留在磁盘上（R-skill-17）。

    **只能在这一刻调用**——`SkillsService.__init__` 里，`runtime.py` 把它挪到
    `app.start_background()` 之前：这是唯一能保证「不可能有 preview 正在写」的
    时刻，因为请求要真正被处理，先得等 HTTP 服务器起来。不靠时间戳之类的启发式
    去猜一个暂存目录「应该」写完了没有——那是拿一个猜测替换一条清楚的不变量，
    `land()` 顶部那条注释同一个道理：串行化窗口窄，直接把它挪到真正没有并发的
    时刻，比拿年龄去猜谁写完了更简单也更对。上一次进程退出前没 install 也没
    discard 的预览，从用户角度看已经作废——重新点一次 preview 不费事。
    """
    staging_root = Path(staging_root)
    if not staging_root.is_dir():
        return
    for stale in staging_root.iterdir():
        _clear(stale)


# 台面用 ThreadingHTTPServer（desk/app.py），一个请求一个线程，land() 之前没有任何
# 东西串行化并发的安装。两个安装同时在飞时，「清掉上一次崩溃留下的痕迹」这条 sweep
# 分不清「崩溃留下的」和「另一个线程正在用的」——不试着靠时间戳、年龄之类的启发式让
# sweep 变聪明（那是拿一个猜测替换一条清楚的不变量，而两个安装真的并发时这个猜测恰好
# 是错的），直接把整个 land() 串行化：装是一个人手动触发的稀有动作，串行化不花什么
# 代价，却能干净地消掉这整类问题（2026-09-23 修复轮 3 finding 1）。
_LAND_LOCK = threading.Lock()


def stage_from_url(url: str, staging_root: Path, fetch) -> dict:
    staging_root = Path(staging_root)
    staging_id = uuid.uuid4().hex
    staged = staging_root / staging_id
    # 下面四个早退都发生在 staged.mkdir() 之前：这个目录还没被创建，没有什么可清的——
    # 清一个不存在的路径是静默的空操作，写成看起来在清理只会让后来的人以为这里有清理
    # 逻辑（2026-09-23 修复轮 1 finding 4）。真正需要清理的是下面写暂存那段。
    try:
        files = fetch(url)
    except Exception as exc:                      # 网络、解析、任何失败都不留痕
        raise InstallError(f"取不下来：{exc}") from exc
    if not isinstance(files, dict) or "SKILL.md" not in files:
        raise InstallError("这个地址里没有 SKILL.md")
    fields, body, error = split_skill(files["SKILL.md"])
    if error:
        raise InstallError(f"SKILL.md 读不通：{error}")
    for required in ("name", "description"):
        if not (fields.get(required) or "").strip():
            raise InstallError(f"frontmatter 缺 {required}")
    # name 校验必须在 staged.mkdir() 之前跑完：一个装不了的 name 要在预览阶段就
    # 被拒绝，用户批准之前就该知道装不了，而不是批准之后才在 land() 里炸掉
    # （2026-09-23 finding 2）。
    _validate_skill_name(fields["name"].strip())

    try:
        staged.mkdir(parents=True, exist_ok=True)
        for filename, text in files.items():
            if not filename.endswith(".md") or "/" in filename or "\\" in filename:
                continue                          # 脚本、二进制、子目录一律不落
            (staged / filename).write_text(text, encoding="utf-8")
    except OSError as exc:
        _clear(staged)
        raise InstallError(f"写暂存失败：{exc}") from exc

    return {"staging_id": staging_id, "name": fields["name"].strip(),
            "description": fields["description"].strip(), "body": body,
            "attachments": sorted(p.name for p in staged.iterdir() if p.name != "SKILL.md")}


def _declared_name(skill_md: Path) -> str | None:
    """读一个已经落盘的 SKILL.md，返回它 frontmatter 里声明的 name；读不出、解析不出
    就返回 None——调用方把 None 当成「不能确认是同一个 skill」处理。"""
    if not skill_md.is_file():
        return None
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    fields, _body, error = split_skill(text)
    if error or not fields:
        return None
    return (fields.get("name") or "").strip()


def land(staging_id: str, staging_root: Path, user_root: Path) -> str:
    # 整个函数都在锁里：sweep、名字校验、拷贝、两次改名——没有一步是安全的部分执行，
    # 全部串行化（2026-09-23 修复轮 3 finding 1）。
    with _LAND_LOCK:
        # staging_id 来自请求体，从没被校验过就直接拼进路径——discard 曾经因此把
        # "../../llms" 当成 staging_id 删掉整个模型库；land 的路径拼接方式更弱但
        # 洞是同一个洞（2026-09-23 finding 1）。
        _validate_staging_id(staging_id)
        staged = Path(staging_root) / staging_id
        if not (staged / "SKILL.md").is_file():
            raise InstallError("暂存已经不在了，请重新预览")
        # 落盘前再读一遍暂存的 SKILL.md，不能假设预览之后它没被动过
        # （2026-09-23 修复轮 1 finding 3）。暂存文件是本地磁盘上的文本文件，理论上
        # 谁都能在预览之后、确认之前手改它——name 也不例外，所以这里必须重新校验
        # name，不能只信任 stage_from_url 在预览阶段做过的那一次（2026-09-23
        # finding 2：校验是规则，下面的路径校验是证明，两者独立）。
        fields, _body, error = split_skill((staged / "SKILL.md").read_text(encoding="utf-8"))
        if error:
            _clear(staged)
            raise InstallError(error)
        name = fields["name"].strip()
        try:
            _validate_skill_name(name)
        except InstallError:
            _clear(staged)
            raise
        user_root = Path(user_root)
        target = user_root / name

        # 带背带的第二证明：name 校验是规则，这条路径校验是证明——一个校验函数
        # 写错，不会连带让另一个也放行。跟 resources/service.py 的
        # `_resolve_delete_target` 同一个做法：先 resolve，再用 is_relative_to
        # 判断包含关系，不匹配就拒绝，而不是先动手再补救（2026-09-23 finding 2）。
        resolved_root = user_root.resolve()
        resolved_target = target.resolve()
        if resolved_target == resolved_root or not resolved_target.is_relative_to(resolved_root):
            _clear(staged)
            raise InstallError(
                f"{name!r} 解析出的路径 {resolved_target} 跑到 {resolved_root} 之外，拒绝安装")

        try:
            user_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            _clear(staged)
            raise InstallError(f"落盘失败：{exc}") from exc

        # 起步先清掉上一次崩溃（断电、被杀）留下的痕迹：崩溃窗口只可能落在下面两次
        # 改名之间，留下的只会是 .incoming-*/.replacing-* 这两类点开头的目录。有了
        # 上面那把锁，这里看到的绝不会是另一个线程正在用的东西——只清这两类前缀，
        # 不做全局扫描式的 sweep（2026-09-23 修复轮 2 finding 3，锁的必要性见
        # 修复轮 3 finding 1：没有锁，这条 sweep 分不清「崩溃留下的」和「另一个线程
        # 正在用的」）。
        for stale in user_root.glob(".incoming-*"):
            _clear(stale)
        for stale in user_root.glob(".replacing-*"):
            _clear(stale)

        # 「路径撞了」不等于「是同一个 skill」：这台设备的文件系统既不区分大小写、也
        # 不做 Unicode 规范化，`Foo` 和 `foo`、NFC 的 `café` 和 NFD 的 `café` 都会落在
        # 同一个路径。只有已存在的目录声明的 name 和这次要装的 name 完全一样，才当成
        # 「重装同一个 skill」去替换；否则拒绝，绝不能把用户认识的另一个 skill 悄悄
        # 换掉——桌面猜不出用户想要哪个，猜错了不可挽回（2026-09-23 修复轮 2
        # finding 2，是修复轮 1 引入的整体替换逻辑本身造出来的洞）。
        if target.exists():
            existing_name = _declared_name(target / "SKILL.md")
            if existing_name is None:
                # 读不出来不等于「是另一个 skill」——那是自相矛盾的说法（同名却说
                # 不是同一个）。说清楚问题在哪：SKILL.md 缺失、读不出或者解析不了，
                # 不敢动这个目录，让用户自己删或者修（2026-09-23 修复轮 3 finding 3）。
                _clear(staged)
                raise InstallError(
                    f"{target.name!r} 这个目录已经存在，但读不出里面的 SKILL.md（缺失、"
                    "读不出，或者解析不了）：没法确认它是不是同一个 skill，不敢动它——"
                    f"先手动删掉或者修好 {target} 再装")
            if existing_name != name:
                _clear(staged)
                raise InstallError(
                    f"{target.name!r} 已经是另一个 skill（叫 {existing_name!r}），这次装的是 "
                    f"{name!r}：文件系统认为路径相同，但不是同一个 skill——"
                    "先给其中一个改名再装")

        # 新版本先整个拷到一个点开头的临时目录——这一步最耗时，但 target 此刻完全没
        # 被动过，拷贝失败也好、进程被杀也好，target 都还是原样。真正有风险的窗口
        # 收窄成下面两次改名之间那一小段，而不是整个拷贝的时长（2026-09-23 修复轮 2
        # finding 3，取代修复轮 1「先挪旧的、再拷新的」的顺序）。
        incoming = user_root / f".incoming-{uuid.uuid4().hex}"
        try:
            shutil.copytree(staged, incoming)
        except OSError as exc:
            _clear(incoming)
            _clear(staged)
            raise InstallError(f"落盘失败：{exc}") from exc

        aside = None
        if target.exists():
            aside = user_root / f".replacing-{uuid.uuid4().hex}"
            try:
                target.rename(aside)
            except OSError as exc:
                # 挪都没挪成功：目标还是原来那份，新版本的临时拷贝清掉，只清暂存。
                _clear(incoming)
                _clear(staged)
                raise InstallError(f"落盘失败：{exc}") from exc

        try:
            incoming.rename(target)
        except OSError as exc:
            if aside is not None:
                try:
                    # 换回旧版本：重装失败不能让用户连能用的版本都丢了。
                    aside.rename(target)
                except OSError as restore_exc:
                    # 双重故障：新版本换不上、旧版本也换不回去。旧版本原样留在
                    # aside，只是名字变了——不能让 restore_exc 就这样原样冒出去：
                    # 那样下面的 InstallError 包装就被跳过了，routes.py 的
                    # except InstallError 接不住，直接变成一次没处理的崩溃，而且
                    # 什么都没告诉用户去哪找回旧版本（2026-09-23 修复轮 3
                    # finding 2）。
                    _clear(incoming)
                    _clear(staged)
                    raise InstallError(
                        f"落盘失败（{exc}），旧版本也没能换回来（{restore_exc}）："
                        f"旧版本原样留在了 {aside}，请手动把它改名或移回 "
                        f"{target}") from restore_exc
            _clear(incoming)
            _clear(staged)
            raise InstallError(f"落盘失败：{exc}") from exc

        if aside is not None:
            _clear(aside)
        _clear(staged)
        return name


def discard(staging_id: str, staging_root: Path) -> None:
    # 同一个洞、更短的路径：discard 一路走到 rmtree，staging_id 一步都没被校验过
    # 就拼进要删的路径——{"staging_id": "../../llms"} 删掉了整个模型库
    # （2026-09-23 finding 1，CRITICAL）。
    _validate_staging_id(staging_id)
    _clear(Path(staging_root) / staging_id)
