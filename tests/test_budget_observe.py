"""R-budget-04：自校准的读数来自 mlx-lm 日志，读不到就是读不到。"""
from desk.budget.observe import parse_cache_line, measured_bytes_per_token

# 真实格式，逐字取自本机 ~/Library/Application Support/LocalModelDesk/logs/mlx-lm.log。
# 注意 "- INFO - " 这个前缀：最初的夹具是我自己编的（没有它），于是一条挡分类型
# 明细行的负向后顾把总数行自己挡掉了，自校准从来没工作过，真机上才抓到。
LOG = """\
2026-09-22 06:12:58,101 - INFO - Starting httpd at 127.0.0.1 on port 8767...
2026-09-22 06:13:00,167 - INFO - Prompt Cache: 1 sequences, 3.20 GB
2026-09-22 06:13:23,888 - INFO - Prompt Cache: 3 sequences, 12.40 GB
2026-09-22 06:13:23,889 - INFO - - QuantizedKVCache: 3 sequences, 12.40 GB
"""


def test_reads_the_last_cache_line_not_the_first():
    """日志里有多轮；预算要的是此刻的占用，不是十分钟前的。"""
    assert parse_cache_line(LOG) == 12_400_000_000


def test_gb_is_decimal_because_mlx_divides_by_1e9():
    assert parse_cache_line("Prompt Cache: 1 sequences, 1.00 GB") == 1_000_000_000


def test_per_type_breakdown_lines_are_not_mistaken_for_the_total():
    """分类型明细行 mlx-lm 打成 "- QuantizedKVCache: …"，不含 "Prompt Cache:" 字面量。

    原先为它加的负向后顾 (?<!- ) 反而把真实日志的总数行挡掉了——真实格式每行
    都有 "… - INFO - " 前缀。守卫多余，靠字面量区分就够。
    """
    assert parse_cache_line("2026-09-22 06:13:23,889 - INFO - - QuantizedKVCache: 3 sequences, 12.40 GB") is None
    # 上面这行的标签是 QuantizedKVCache，本就不含 "Prompt Cache:" 字样，
    # 删掉正则里的 (?<!- ) 守卫也测不出来——必须用一条真正以 "- " 开头、
    # 但字面量仍是 "Prompt Cache:" 的行才能咬到那个守卫。
    # 曾经这里还有一条 `- Prompt Cache: …` 的断言。那是当初为了让这条测试「能变红」
    # 而构造出来的输入——mlx-lm 从不产生它，而为了让它通过加的负向后顾，
    # 恰恰把真实日志的总数行挡掉了。删掉虚构的输入，保留真实的那条。


def test_absent_line_reports_nothing():
    assert parse_cache_line("nothing interesting here") is None


def test_changed_format_reports_nothing_rather_than_guessing():
    """mlx-lm 改了格式就老实说读不到，不猜。"""
    assert parse_cache_line("Prompt Cache: 3 seqs / 12.40 gigabytes") is None


def test_bytes_per_token_is_the_quotient():
    assert measured_bytes_per_token(12_400_000_000, 40_000) == 310_000


def test_zero_tokens_reports_nothing_instead_of_dividing_by_zero():
    assert measured_bytes_per_token(12_400_000_000, 0) is None


def test_missing_cache_reading_reports_nothing():
    assert measured_bytes_per_token(None, 40_000) is None
