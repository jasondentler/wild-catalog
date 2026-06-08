from wild_catalog.prior.build.builder import (
    _format_count_progress,
    _format_duration,
    _format_progress,
)


def test_format_progress_includes_percent_counts_and_eta() -> None:
    progress = _format_progress(
        processed_count=25,
        total_count=100,
        elapsed_seconds=50,
    )

    assert progress == "25.0% complete (25/100 ranges), ETA 2m 30s"


def test_format_progress_handles_unknown_total() -> None:
    progress = _format_progress(
        processed_count=25,
        total_count=0,
        elapsed_seconds=50,
    )

    assert progress == "progress unknown (25 processed), ETA unknown"


def test_format_duration_uses_compact_units() -> None:
    assert _format_duration(None) == "unknown"
    assert _format_duration(12.9) == "12s"
    assert _format_duration(125.0) == "2m 5s"
    assert _format_duration(3725.0) == "1h 2m 5s"


def test_format_count_progress_uses_item_name() -> None:
    progress = _format_count_progress(
        processed_count=2,
        total_count=4,
        elapsed_seconds=20,
        item_name="archives",
    )

    assert progress == "50.0% complete (2/4 archives), ETA 20s"
