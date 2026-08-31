from desk.resources.events import ResourceEvents


def test_progress_subscribers_called_in_order():
    ev = ResourceEvents()
    seen = []
    ev.subscribe_progress(lambda p: seen.append(("a", p)))
    ev.subscribe_progress(lambda p: seen.append(("b", p)))

    ev.emit_progress("snapshot")

    assert seen == [("a", "snapshot"), ("b", "snapshot")]


def test_finished_subscribers_receive_progress_and_final_status():
    ev = ResourceEvents()
    seen = []
    ev.subscribe_finished(lambda p, s: seen.append((p, s)))

    ev.emit_finished("progress", "status")
    ev.emit_finished("progress-only")

    assert seen == [("progress", "status"), ("progress-only", None)]


def test_raising_subscriber_does_not_break_the_emit(caplog):
    ev = ResourceEvents()
    seen = []

    def boom(p):
        raise RuntimeError("subscriber bug")

    ev.subscribe_progress(boom)
    ev.subscribe_progress(seen.append)

    ev.emit_progress("x")

    assert seen == ["x"]
    assert any("downloadProgressed" in record.message for record in caplog.records)
