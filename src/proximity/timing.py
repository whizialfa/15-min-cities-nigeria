"""Append wall-clock times to notes/task_times.md."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from .paths import ROOT

LOG = ROOT / "notes" / "task_times.md"


def _now() -> datetime:
    return datetime.now().astimezone()


def append(line: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if not LOG.exists():
        LOG.write_text(
            "# Task times\n\n"
            "Wall-clock times for work Wisdom asked for. Local time. "
            "Stage seconds are `time.perf_counter` on this machine.\n\n",
            encoding="utf-8",
        )
    text = line.rstrip() + "\n"
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(text)
    print(text, end="", flush=True)


def start(task: str, note: str = "") -> float:
    extra = f" — {note}" if note else ""
    append(f"- `{_now().strftime('%Y-%m-%d %H:%M:%S %Z')}` start **{task}**{extra}")
    return time.perf_counter()


def done(task: str, t0: float, note: str = "") -> float:
    dt = time.perf_counter() - t0
    extra = f" — {note}" if note else ""
    append(
        f"- `{_now().strftime('%Y-%m-%d %H:%M:%S %Z')}` done **{task}** in "
        f"**{dt / 60:.1f} min** ({dt:.0f} s){extra}"
    )
    return dt
