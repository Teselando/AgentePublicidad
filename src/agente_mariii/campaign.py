"""Ciclo de tandas basado en el Top visible y envíos confirmados."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .core import MADRID, cell, parse_date


@dataclass(frozen=True)
class TopGroup:
    group_id: str
    name: str
    family: str


def sheet_date(day: date) -> int:
    return (day - date(1899, 12, 30)).days


def top_groups(sheet, limit: int = 30) -> list[TopGroup]:
    """Lee el resultado calculado por la pestaña, no un ranking paralelo."""
    if not 1 <= limit <= 30:
        raise ValueError("El límite debe estar entre 1 y 30.")
    rows = sheet.rows("Top recomendaciones", "A7:J36")
    result: list[TopGroup] = []
    seen: set[str] = set()
    for row in rows:
        group_id = cell(row, 9)
        if not group_id.startswith("G") or not group_id[1:].isdigit():
            continue
        if group_id in seen:
            raise ValueError(f"ID repetido en el Top: {group_id}.")
        seen.add(group_id)
        result.append(TopGroup(group_id, cell(row, 1), cell(row, 2)))
        if len(result) >= limit:
            break
    return result


def parse_sent_at(value: str) -> datetime:
    when = datetime.fromisoformat(value)
    if when.tzinfo is None:
        when = when.replace(tzinfo=MADRID)
    return when.astimezone(MADRID)


def record_confirmed_batch(sheet, confirmations: list[dict], *, require_top: bool = True) -> list[str]:
    """Valida toda la tanda antes de escribir una sola fila.

    Cada confirmación debe tener group_id y sent_at. El acto de preparar una
    tanda no prueba que se enviara un mensaje; solo esta confirmación lo anota.
    """
    if not confirmations:
        raise ValueError("La tanda no contiene envíos confirmados.")
    groups = sheet.rows("Grupos", "A2:N1000")
    history = sheet.rows("Historial", "A2:I1000")
    by_id = {cell(row, 0): row for row in groups if cell(row, 0)}
    allowed = {item.group_id for item in top_groups(sheet)} if require_top else set()
    existing = set()
    for row in history:
        try:
            day = parse_date(cell(row, 1))
        except ValueError:
            continue
        if day:
            existing.add((cell(row, 3), day))

    next_id = max(
        (int(cell(row, 0)[1:]) for row in history
         if cell(row, 0).startswith("E") and cell(row, 0)[1:].isdigit()),
        default=0,
    )
    additions = []
    ids = []
    for item in confirmations:
        group_id = item.get("group_id", "")
        if group_id not in by_id:
            raise ValueError(f"Grupo desconocido: {group_id}.")
        if require_top and group_id not in allowed:
            raise ValueError(f"{group_id} no figura en el Top actual; no se anotó la tanda.")
        if not isinstance(item.get("sent_at"), str):
            raise ValueError(f"Falta sent_at para {group_id}.")
        when = parse_sent_at(item["sent_at"])
        key = (group_id, when.date())
        if key in existing:
            raise ValueError(f"Ya hay un envío registrado el {when.date():%d/%m/%Y} para {group_id}.")
        existing.add(key)
        next_id += 1
        group = by_id[group_id]
        note = str(item.get("notes", "")).strip()
        evidence = str(item.get("evidence", "")).strip()
        if not evidence:
            raise ValueError(f"Falta evidencia de confirmación para {group_id}.")
        parts = [f"Envío confirmado; hora Europe/Madrid {when:%H:%M}", f"evidencia: {evidence}"]
        if note:
            parts.append(note)
        additions.append([
            f"E{next_id:04d}", sheet_date(when.date()), cell(group, 1),
            group_id, cell(group, 2), "", "", "", ". ".join(parts),
        ])
        ids.append(group_id)
    sheet.append("Historial", "A:I", additions)
    return ids
