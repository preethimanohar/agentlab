"""Tiny task dispatcher so there's one obvious entry point.

    uv run python tasks.py <task> [args...]
    uv run python tasks.py            # list tasks
"""

from __future__ import annotations

import runpy
import sys

TASKS = {
    # data pipeline
    "ingest":       ("pipeline.ingest",           "freeze an immutable NYC inspection snapshot"),
    "profile":      ("pipeline.profile",          "write reports/raw_profile.md"),
    "canonical":    ("pipeline.canonical",        "build data/generated/canonical.duckdb"),
    "peek":         ("pipeline.peek",             "guided tour of the data product"),
    "sql":          ("pipeline.query",            'run raw SQL: tasks.py sql "SELECT ..."'),
    "ground-truth": ("evals.compute_ground_truth", "compute the benchmark answer key"),
    # agents (interactive pokes; filmable versions are in demos/)
    "ask":          ("agent.ask_cli",             'ask the model anything: tasks.py ask "..."'),
    "raw":          ("agent.raw_agent",           'naive baseline agent: tasks.py raw [--show] "..."'),
    "sqlagent":     ("agent.sql_agent",           'SQL agent: tasks.py sqlagent [--show] "..."'),
    # demos
    "demo":         ("demos.run",                 "run a filmable demo: tasks.py demo [NN]"),
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in TASKS:
        print("tasks:\n")
        for name, (_, desc) in TASKS.items():
            print(f"  {name:<13} {desc}")
        raise SystemExit(0 if len(sys.argv) < 2 else 1)
    module = TASKS[sys.argv[1]][0]
    sys.argv = [sys.argv[0], *sys.argv[2:]]  # forward remaining args to the module
    runpy.run_module(module, run_name="__main__")


if __name__ == "__main__":
    main()
