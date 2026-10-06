"""CLI manual y programación semanal opcional."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json

from .core import MADRID, cell, madrid_now, normalized_name, parse_date, recommendations
from .discovery import search
from .sheets import Sheet


def numbered_id(rows: list[list[str]], prefix: str) -> int:
    return max((int(cell(r, 0)[1:]) for r in rows if cell(r, 0).startswith(prefix) and cell(r, 0)[1:].isdigit()), default=0)


def sheet_date(day: date) -> int:
    """Google Sheets date serial; destination columns already use DD/MM/YYYY."""
    return (day - date(1899, 12, 30)).days


def recommend(sheet: Sheet, amount: int) -> None:
    groups = sheet.rows("Grupos", "A2:N1000")
    history = sheet.rows("Historial", "A2:I1000")
    config = sheet.rows("Configuración", "A2:H1000")
    settings = {cell(r, 0): cell(r, 1) for r in config}
    pending = {cell(r, 6) for r in config if cell(r, 7).startswith("Pendiente")}
    choices = recommendations(
        groups, history, today=madrid_now().date(),
        group_days=int(settings.get("Cooldown mismo grupo") or 30),
        family_days=int(settings.get("Cooldown misma familia") or 7),
        limit=amount, pending_ids=pending,
    )
    for i, item in enumerate(choices, 1):
        print(f"{i:2}. {item.name} [{item.group_id}] · {item.family or 'Gestor desconocido'} · {item.reason}")
    if not choices:
        print("No hay grupos elegibles con las reglas actuales.")


def record_send(sheet: Sheet, identifier: str, at: str | None, notes: str, force: bool) -> None:
    groups = sheet.rows("Grupos", "A2:N1000")
    history = sheet.rows("Historial", "A2:I1000")
    matches = [r for r in groups if cell(r, 0) == identifier or normalized_name(cell(r, 1)) == normalized_name(identifier)]
    if len(matches) != 1:
        raise ValueError(f"Se necesita un grupo inequívoco; coincidencias: {len(matches)}. Usa su ID Gxxxx.")
    group = matches[0]
    when = datetime.fromisoformat(at) if at else madrid_now()
    if when.tzinfo is None:
        when = when.replace(tzinfo=MADRID)
    else:
        when = when.astimezone(MADRID)
    day = when.date()
    if not force and any(cell(r, 3) == cell(group, 0) and parse_date(cell(r, 1)) == day for r in history):
        raise ValueError("Ya existe un envío de este grupo en esa fecha; revisa Historial o usa --force.")
    next_id = numbered_id(history, "E") + 1
    row = [f"E{next_id:04d}", sheet_date(day), cell(group, 1), cell(group, 0), cell(group, 2), "", "", "",
           f"Envío declarado por el usuario; hora Europe/Madrid {when:%H:%M}. {notes}".strip()]
    sheet.append("Historial", "A:I", [row])
    print(f"Registrado {row[0]} · {row[2]} · {day:%d/%m/%Y}. La hoja recalcula los plazos.")


def discover(sheet: Sheet | None, *, write: bool, limit: int) -> None:
    findings = search(limit=limit)
    if not write:
        print(json.dumps([f.__dict__ for f in findings], ensure_ascii=False, indent=2))
        return
    assert sheet is not None
    existing = sheet.rows("Grupos descubiertos", "A2:Q1000")
    seen = {cell(r, 6).split("?")[0].rstrip("/") for r in existing if cell(r, 6)}
    next_id = numbered_id(existing, "D")
    today = sheet_date(madrid_now().date())
    new_rows = []
    for finding in findings:
        if finding.invitation in seen:
            continue
        next_id += 1
        seen.add(finding.invitation)
        new_rows.append([
            f"D{next_id:04d}", finding.reference, "", "", "", "", finding.invitation,
            finding.source, "", "Desconocida", "Fuente pública; administrador no comprobado.",
            "Enlace publicado; sin nombre visible", "Revisar enlace", "Media", "", today, today,
        ])
    sheet.append("Grupos descubiertos", "A:Q", new_rows)
    print(f"{len(new_rows)} candidatos nuevos. No se han añadido a Grupos ni al Top.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gestor de grupos vinculado a Google Sheets")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("recommend").add_argument("--limit", type=int, default=30)
    sent = sub.add_parser("record-send")
    sent.add_argument("group", help="ID Gxxxx o nombre exacto")
    sent.add_argument("--at", help="Fecha/hora ISO local Europe/Madrid, por ejemplo 2026-10-06T20:30")
    sent.add_argument("--notes", default="")
    sent.add_argument("--force", action="store_true", help="Permite más de un envío al mismo grupo y fecha")
    found = sub.add_parser("discover")
    found.add_argument("--write", action="store_true", help="Añadir nuevos hallazgos a la pestaña, sin incorporarlos a Grupos")
    found.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    if args.command == "discover":
        discover(Sheet() if args.write else None, write=args.write, limit=args.limit)
    elif args.command == "recommend":
        recommend(Sheet(), args.limit)
    else:
        record_send(Sheet(), args.group, args.at, args.notes, args.force)


if __name__ == "__main__":
    main()
