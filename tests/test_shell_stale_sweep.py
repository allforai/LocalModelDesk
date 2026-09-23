"""跑 GUI 外壳测试之前，先扫掉上次遗留的外壳进程。

为什么是「跑之前扫」而不是「跑完清干净」：fixture 的 teardown 只在 pytest 正常
走完时执行，而 pytest 被 SIGKILL（超时、手工 kill、CI 掐断）时一行都不跑。
被它 spawn 出来的外壳于是成为孤儿（父进程变成 launchd），而且它是 GUI 程序、
会抢焦点——下一次跑同一批测试就报 window_not_focused。这是个自我加重的循环：
跑测试 → 被中断 → 漏一个 GUI 进程 → 下次更容易失败 → 更容易被中断。

清理不能保证，清理**前**的自查可以。
"""
from shell_helpers import stale_shell_app_pids

REAL_APP = "  30794   /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/MacOS/LocalModelDesk"
STALE = "   9532   /var/folders/yk/1lz/T/shellapp-3sp5rr7m/LocalModelDeskShell"
OTHER = "  12345   /usr/bin/python3 -m pytest tests"


def test_finds_a_leftover_temp_shell_app():
    assert stale_shell_app_pids(STALE) == [9532]


def test_never_touches_a_shell_binary_outside_the_temp_dir():
    """同名但不在临时目录里的外壳不许动——那可能是开发者自己编译、正在用的一份。

    这条是「限定必须在 shellapp- 目录下」那半条规则的唯一证据：去掉目录限定后
    只有这条会红（用户装的 app 二进制叫 LocalModelDesk，不带 Shell，本来就不匹配）。
    """
    local_build = "  4242   /Users/aa/LocalModelDesk/build/LocalModelDeskShell"
    assert stale_shell_app_pids(local_build) == []
    assert stale_shell_app_pids("\n".join([local_build, STALE])) == [9532]


def test_never_touches_the_installed_app():
    """用户正开着的那个 app 长得很像，但它不在临时目录里——杀错了是毁用户的东西。"""
    assert stale_shell_app_pids(REAL_APP) == []
    assert stale_shell_app_pids("\n".join([REAL_APP, STALE, OTHER])) == [9532]


def test_unrelated_processes_are_not_matched():
    assert stale_shell_app_pids(OTHER) == []


def test_junk_lines_do_not_crash_or_match():
    assert stale_shell_app_pids("") == []
    assert stale_shell_app_pids("没有 pid 的一行 shellapp-xxx/LocalModelDeskShell") == []


def test_the_sweeper_itself_is_not_matched():
    """扫除命令自己的命令行里会出现这个模式——匹配到自己就等于杀自己。

    今天真踩过同形的坑：一个等待循环写成 `until ! ps aux | grep -q "[p]ytest"`，
    而 ps 会列出这条命令自身、其命令行里正含着那个模式，于是它在等自己结束，
    跑了 7 小时 37 分。
    """
    sweeper = '  55555   /bin/zsh -c ps -eo pid,comm | grep shellapp-/LocalModelDeskShell'
    assert stale_shell_app_pids(sweeper) == []
