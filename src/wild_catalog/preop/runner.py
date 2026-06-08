import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed

from wild_catalog.preop.tasks import PreOperationalTask

logger = logging.getLogger(__name__)


def run_preoperational_tasks(
    tasks: Sequence[PreOperationalTask],
    *,
    max_workers: int | None = None,
) -> None:
    if not tasks:
        return

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for task in tasks:
            logger.info("Starting pre-operational task: %s", task.name)
            futures[executor.submit(task.run)] = task
        failures: list[tuple[str, BaseException]] = []

        for future in as_completed(futures):
            task = futures[future]

            try:
                future.result()
                logger.info("Completed pre-operational task: %s", task.name)
            except BaseException as exc:
                logger.exception("Failed pre-operational task: %s", task.name)
                failures.append((task.name, exc))

        if failures:
            names = ", ".join(name for name, _ in failures)
            raise RuntimeError(f"Pre-operational task failure(s): {names}") from failures[0][1]
