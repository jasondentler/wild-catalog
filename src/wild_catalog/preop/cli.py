import logging

from wild_catalog.core.config import Settings
from wild_catalog.preop.runner import run_preoperational_tasks
from wild_catalog.preop.tasks import FunctionPreOperationalTask
from wild_catalog.prior.build.builder import build_inat21_range_map_store


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()

    tasks = [
        FunctionPreOperationalTask(
            name="build-inat21-range-map-store",
            action=lambda: build_inat21_range_map_store(settings),
        ),
    ]

    run_preoperational_tasks(tasks)


if __name__ == "__main__":
    main()
