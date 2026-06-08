import pytest

from wild_catalog.preop.runner import run_preoperational_tasks
from wild_catalog.preop.tasks import FunctionPreOperationalTask


def test_run_preoperational_tasks_runs_all_tasks() -> None:
    completed: list[str] = []

    tasks = [
        FunctionPreOperationalTask(
            name="first",
            action=lambda: completed.append("first"),
        ),
        FunctionPreOperationalTask(
            name="second",
            action=lambda: completed.append("second"),
        ),
    ]

    run_preoperational_tasks(tasks, max_workers=2)

    assert sorted(completed) == ["first", "second"]


def test_run_preoperational_tasks_raises_if_task_fails() -> None:
    def fail() -> None:
        raise ValueError("boom")

    tasks = [
        FunctionPreOperationalTask(
            name="failing-task",
            action=fail,
        ),
    ]

    with pytest.raises(RuntimeError, match="failing-task"):
        run_preoperational_tasks(tasks, max_workers=1)


def test_run_preoperational_tasks_accepts_empty_task_list() -> None:
    run_preoperational_tasks([])
