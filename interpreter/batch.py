"""
Batch processing for pill.ai — run multiple tasks against one Interpreter.

Pattern from relay-master: queue tasks, run sequentially (or concurrently up
to `max_workers`), collect structured results with per-task cost tracking.

Usage:
    from interpreter.batch import BatchProcessor
    from interpreter.core.core import Interpreter

    ai = Interpreter()
    bp = BatchProcessor(ai)

    results = bp.run([
        "summarize ~/Documents/report.pdf",
        "list the 5 largest files in ~/Downloads",
        "write a Python script that pings google.com 3 times",
    ])

    for r in results:
        print(r.task, "→", r.status, f"(${r.cost_usd:.4f})")
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class TaskResult:
    task: str
    status: str        # "ok" | "error" | "budget_exceeded"
    output: str
    cost_usd: float
    duration_s: float
    error: Optional[str] = None
    new_skill: Optional[str] = None


@dataclass
class BatchResult:
    results: List[TaskResult] = field(default_factory=list)

    @property
    def total_cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.results)

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.status == "ok")

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.status != "ok")

    def summary(self) -> str:
        lines = [
            f"Batch: {len(self.results)} tasks — "
            f"{self.ok_count} ok / {self.error_count} errors — "
            f"${self.total_cost_usd:.4f} total"
        ]
        for r in self.results:
            mark = "✓" if r.status == "ok" else "✗"
            lines.append(f"  {mark} [{r.duration_s:.1f}s] {r.task[:60]}")
        return "\n".join(lines)


class BatchProcessor:
    """
    Runs a list of tasks through an Interpreter instance.

    Sequential mode (default): tasks run one-at-a-time, sharing conversation
    context if `shared_context=True`.

    Parallel mode (`max_workers > 1`): each task gets its own fresh Interpreter
    instance (safe — no shared state). Useful for independent tasks.
    """

    def __init__(
        self,
        interpreter,
        max_workers: int = 1,
        shared_context: bool = False,
        reset_between_tasks: bool = True,
        on_result=None,    # callback(TaskResult) called after each task
    ):
        self._interpreter = interpreter
        self.max_workers = max_workers
        self.shared_context = shared_context
        self.reset_between_tasks = reset_between_tasks
        self.on_result = on_result

    def run(self, tasks: List[str]) -> BatchResult:
        if self.max_workers > 1:
            return self._run_parallel(tasks)
        return self._run_sequential(tasks)

    # ── Sequential ────────────────────────────────────────────────────────

    def _run_sequential(self, tasks: List[str]) -> BatchResult:
        batch = BatchResult()
        for task in tasks:
            result = self._run_one(self._interpreter, task)
            batch.results.append(result)
            if self.on_result:
                self.on_result(result)
            if self.reset_between_tasks and not self.shared_context:
                self._interpreter.reset()
        return batch

    # ── Parallel ──────────────────────────────────────────────────────────

    def _run_parallel(self, tasks: List[str]) -> BatchResult:
        from interpreter.core.core import Interpreter
        batch = BatchResult()
        futures = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            for task in tasks:
                ai = Interpreter(
                    model=self._interpreter.model,
                    safe_mode=self._interpreter.safe_mode,
                    verbose=self._interpreter.verbose,
                )
                futures[pool.submit(self._run_one, ai, task)] = task

            for future in as_completed(futures):
                result = future.result()
                batch.results.append(result)
                if self.on_result:
                    self.on_result(result)

        # Re-order to match original task order
        order = {t: i for i, t in enumerate(tasks)}
        batch.results.sort(key=lambda r: order.get(r.task, 0))
        return batch

    # ── Single task ───────────────────────────────────────────────────────

    def _run_one(self, ai, task: str) -> TaskResult:
        cost_before = ai._router.session_cost
        t0 = time.monotonic()
        try:
            output = ai.chat(task, display=False) or ""
            duration = time.monotonic() - t0
            cost = ai._router.session_cost - cost_before
            return TaskResult(
                task=task,
                status="ok",
                output=str(output),
                cost_usd=cost,
                duration_s=duration,
            )
        except Exception as e:
            duration = time.monotonic() - t0
            status = "budget_exceeded" if "budget" in str(e).lower() else "error"
            return TaskResult(
                task=task,
                status=status,
                output="",
                cost_usd=0.0,
                duration_s=duration,
                error=str(e),
            )
