import logging
from collections.abc import Sequence

from wild_catalog.core.config import Settings
from wild_catalog.preop.runner import run_preoperational_tasks
from wild_catalog.preop.tasks import FunctionPreOperationalTask, PreOperationalTask
from wild_catalog.prior.build.builder import build_inat21_range_map_store
from wild_catalog.taxonomy.dwca import download_taxonomy_dwca


def build_preoperational_tasks(settings: Settings) -> Sequence[PreOperationalTask]:
    return (
        FunctionPreOperationalTask(
            name="download-taxonomy-dwca",
            action=lambda: download_taxonomy_dwca(settings),
        ),
        FunctionPreOperationalTask(
            name="build-inat21-range-map-store",
            action=lambda: build_inat21_range_map_store(settings),
        ),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()
    tasks = build_preoperational_tasks(settings)

    run_preoperational_tasks(tasks)


if __name__ == "__main__":
    main()
