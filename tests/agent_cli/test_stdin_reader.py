"""ask 读管道输入（A-12，G8）：没人写的管道不能把命令挂死。"""
import io
import os
import threading
import time

import pytest

from desk.agent_cli.errors import CliError, EXIT_TIMEOUT, EXIT_USAGE
from desk.agent_cli.stdin_reader import read_piped


def _pipe():
    r, w = os.pipe()
    return os.fdopen(r, "r"), w


def test_open_pipe_without_data_is_ignored_after_the_idle_window():
    reader, w = _pipe()
    err = io.StringIO()
    start = time.monotonic()
    try:
        assert read_piped(reader, deadline_s=60, idle_s=0.2, err=err) == ""
    finally:
        os.close(w)
        reader.close()
    assert time.monotonic() - start < 2
    assert "没有数据" in err.getvalue()


def test_closed_pipe_with_data_is_read_whole():
    reader, w = _pipe()
    os.write(w, "管道内容".encode())
    os.close(w)
    assert read_piped(reader, deadline_s=60, idle_s=0.2, err=io.StringIO()) == "管道内容"
    reader.close()


def test_slow_producer_that_starts_inside_the_window_is_read():
    reader, w = _pipe()

    def produce():
        time.sleep(0.1); os.write(w, b"late "); time.sleep(0.1); os.write(w, b"data"); os.close(w)

    threading.Thread(target=produce).start()
    assert read_piped(reader, deadline_s=60, idle_s=1.0, err=io.StringIO()) == "late data"
    reader.close()


def test_data_that_never_ends_times_out_with_exit_3():
    reader, w = _pipe()
    os.write(w, b"partial")
    with pytest.raises(CliError) as exc:
        read_piped(reader, deadline_s=0.3, idle_s=0.2, err=io.StringIO())
    assert exc.value.exit_code == EXIT_TIMEOUT
    os.close(w)
    reader.close()


def test_non_utf8_input_is_exit_2():
    reader, w = _pipe()
    os.write(w, "中文".encode("gbk"))
    os.close(w)
    with pytest.raises(CliError) as exc:
        read_piped(reader, deadline_s=60, idle_s=0.2, err=io.StringIO())
    assert exc.value.exit_code == EXIT_USAGE
    reader.close()


def test_dev_null_and_in_memory_text():
    with open(os.devnull) as devnull:
        assert read_piped(devnull, deadline_s=60, idle_s=0.2, err=io.StringIO()) == ""
    assert read_piped(io.StringIO("内存里的"), deadline_s=60, idle_s=0.2, err=io.StringIO()) == "内存里的"
    assert read_piped(None, deadline_s=60, err=io.StringIO()) == ""
