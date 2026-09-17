"""R-budget-04：自校准的读数来自 mlx-lm 日志，读不到就是读不到。"""
from desk.budget.observe import parse_cache_line, measured_bytes_per_token

LOG = """\
2026-09-17 10:00:01 INFO Starting server on 127.0.0.1:8767
2026-09-17 10:02:11 INFO Prompt Cache: 1 sequences, 3.20 GB
2026-09-17 10:05:42 INFO Prompt Cache: 3 sequences, 12.40 GB
2026-09-17 10:05:42 INFO - QuantizedKVCache: 3 sequences, 12.40 GB
"""


def test_reads_the_last_cache_line_not_the_first():
    """日志里有多轮；预算要的是此刻的占用，不是十分钟前的。"""
    assert parse_cache_line(LOG) == 12_400_000_000


def test_gb_is_decimal_because_mlx_divides_by_1e9():
    assert parse_cache_line("Prompt Cache: 1 sequences, 1.00 GB") == 1_000_000_000


def test_per_type_breakdown_lines_are_not_mistaken_for_the_total():
    """以 '- ' 开头的是分类型明细，累加进总数会让读数翻倍。"""
    assert parse_cache_line("- QuantizedKVCache: 3 sequences, 12.40 GB") is None
    # 上面这行的标签是 QuantizedKVCache，本就不含 "Prompt Cache:" 字样，
    # 删掉正则里的 (?<!- ) 守卫也测不出来——必须用一条真正以 "- " 开头、
    # 但字面量仍是 "Prompt Cache:" 的行才能咬到那个守卫。
    assert parse_cache_line("- Prompt Cache: 3 sequences, 12.40 GB") is None


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
