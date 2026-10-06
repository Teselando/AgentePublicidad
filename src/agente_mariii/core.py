"""Reglas puras de selección y fechas. La hoja conserva el historial."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import re
import unicodedata

MADRID = ZoneInfo("Europe/Madrid")
PRACTICAL = re.compile(
    r"ingenier|\bing\.?\b|inform[aá]tic|software|programaci|matem[aá]tic|"
    r"\bmates\b|c[aá]lculo|estad[ií]stic|arquitect|econom|\bade\b|"
    r"finanz|contabil|\bdam\b|\bdaw\b|\basir\b|\bsmr\b|electr|"
    r"rob[oó]tic|mecatr|automoci|paisaj|bach|\b4.{0,4}eso\b|"
    r"evau|ebau|\bpau\b|inteligencia artificial|ciencia de datos",
    re.IGNORECASE,
)


def madrid_now() -> datetime:
    return datetime.now(MADRID)


def parse_date(value: str) -> date | None:
    if not value or value in {"Nunca", "Sin registro"}:
        return None
    return datetime.strptime(value, "%d/%m/%Y").date()


def normalized_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(value.split())


def cell(row: list[str], index: int) -> str:
    return row[index] if index < len(row) else ""


@dataclass(frozen=True)
class Candidate:
    group_id: str
    name: str
    family: str
    confidence: str
    last_send: date | None
    sends: int
    priority: str
    reason: str


def recommendations(
    groups: list[list[str]],
    history: list[list[str]],
    *,
    today: date,
    group_days: int = 30,
    family_days: int = 7,
    limit: int = 30,
    pending_ids: set[str] | None = None,
) -> list[Candidate]:
    """Prioriza grupos disponibles y elige uno por posible gestor.

    Cero envíos significa cero *registrados*. Una familia Media se evita durante
    la misma fecha de una tanda, sin aplicarle automáticamente siete días.
    """
    pending_ids = pending_ids or set()
    by_group: dict[str, list[date]] = {}
    by_family: dict[str, list[date]] = {}
    unknown_dates: list[date] = []
    for row in history:
        try:
            sent = parse_date(cell(row, 1))
        except ValueError:
            continue
        if not sent:
            continue
        group_id, family = cell(row, 3), cell(row, 4)
        by_group.setdefault(group_id, []).append(sent)
        if family:
            by_family.setdefault(family, []).append(sent)
        else:
            unknown_dates.append(sent)

    ranked: list[Candidate] = []
    for row in groups:
        group_id, name, family = cell(row, 0), cell(row, 1), cell(row, 2)
        confidence, priority, state = cell(row, 3), cell(row, 9), cell(row, 10)
        if not group_id or not name or group_id in pending_ids:
            continue
        if state in {"Pausado", "No contactar"} or name == family:
            continue
        sends = by_group.get(group_id, [])
        last = max(sends) if sends else None
        if last and today < last + timedelta(days=group_days):
            continue
        family_sends = by_family.get(family, []) if family else unknown_dates
        if family_sends:
            latest_family = max(family_sends)
            if latest_family == today:
                continue  # la tanda actual ya tocó a ese posible gestor
            if family and confidence in {"Alta", "Confirmada"} and today < latest_family + timedelta(days=family_days):
                continue
        if not PRACTICAL.search(name):
            continue  # no rellenar el top con áreas de encaje débil
        reason = "Sin envíos registrados" if not last else f"Último envío: {last:%d/%m/%Y}"
        ranked.append(Candidate(group_id, name, family, confidence, last, len(sends), priority or "Media", reason))

    priority_order = {"Alta": 0, "Media": 1, "Baja": 2}
    confidence_order = {"Confirmada": 0, "Alta": 1, "Media": 2, "Baja": 3, "Desconocida": 4}
    ranked.sort(key=lambda c: (
        c.sends > 0, priority_order.get(c.priority, 1),
        -(today - c.last_send).days if c.last_send else 0,
        confidence_order.get(c.confidence, 4), c.group_id,
    ))
    chosen: list[Candidate] = []
    used: set[str] = set()
    for candidate in ranked:
        key = candidate.family or "__administracion_desconocida__"
        if key not in used:
            chosen.append(candidate)
            used.add(key)
        if len(chosen) >= limit:
            break
    return chosen


def next_send_date(day: date, cooldown: int = 30) -> date:
    return day + timedelta(days=cooldown)
