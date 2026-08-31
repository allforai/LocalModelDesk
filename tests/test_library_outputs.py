"""Range planning follows RFC 7233's single-range rules."""

import pytest

from desk.library.outputs import parse_range


@pytest.mark.parametrize(
    ("size", "header", "status", "start", "length"),
    [
        (10, None, 200, 0, 10),
        (10, "items=0-1", 200, 0, 10),
        (10, "bytes=wat", 200, 0, 10),
        (10, "bytes=0-1,4-5", 200, 0, 10),
        (10, "bytes=2-20", 206, 2, 8),
        (10, "bytes=3-", 206, 3, 7),
        (10, "bytes=-3", 206, 7, 3),
        (10, "bytes=-20", 206, 0, 10),
        (10, "bytes=10-", 416, None, 0),
        (10, "bytes=-0", 416, None, 0),
        (0, "bytes=0-0", 416, None, 0),
    ],
)
def test_parse_range_rfc7233_single_range(size, header, status, start, length):
    plan = parse_range(size, header)

    assert (plan.status, plan.start, plan.length) == (status, start, length)


@pytest.mark.parametrize("header", ["bytes=6-5", "bytes=-", "bytes=--1", "bytes=+1-2"])
def test_parse_range_invalid_syntax_falls_back_to_full_file(header):
    plan = parse_range(10, header)

    assert (plan.status, plan.start, plan.length) == (200, 0, 10)
