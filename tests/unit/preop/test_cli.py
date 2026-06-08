from wild_catalog.core.config import Settings
from wild_catalog.preop.cli import build_preoperational_tasks


def test_build_preoperational_tasks_includes_taxonomy_download() -> None:
    tasks = build_preoperational_tasks(Settings())

    assert [task.name for task in tasks] == [
        "download-taxonomy-dwca",
        "build-inat21-range-map-store",
    ]
