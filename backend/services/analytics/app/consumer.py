"""Outbox event consumer helpers.

The deployment worker can call :func:`consume_batch` with rows read from Redis
Streams or a database outbox.  A checkpoint set prevents a retried message from
inflating a report.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .main import Event, consume_event


def consume_batch(
    rows: Iterable[dict[str, Any]],
    aggregates: dict[str, dict[str, dict[str, Any]]],
    processed_ids: set[str],
) -> int:
    processed = 0
    for row in rows:
        event_id = str(row.get("id") or row.get("eventId") or "")
        if event_id and event_id in processed_ids:
            continue
        event = Event.model_validate(row)
        consume_event(aggregates, event)
        if event_id:
            processed_ids.add(event_id)
        processed += 1
    return processed
