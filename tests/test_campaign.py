import unittest
from datetime import date, timedelta

from agente_mariii.campaign import record_confirmed_batch, top_groups
from agente_mariii.core import recommendations


class FakeSheet:
    def __init__(self):
        self.data = {
            "Top recomendaciones": [
                ["1", "Ingeniería Informática", "Red A", "", "", "", "", "", "", "G0001"],
                ["2", "Matemáticas", "Red B", "", "", "", "", "", "", "G0002"],
            ],
            "Grupos": [
                ["G0001", "Ingeniería Informática", "Red A", "Media", "No", "", "", "", "0", "Media", "Disponible"],
                ["G0002", "Matemáticas", "Red B", "Media", "No", "", "", "", "0", "Media", "Disponible"],
            ],
            "Historial": [],
        }
        self.writes = []

    def rows(self, tab, a1):
        return self.data[tab]

    def append(self, tab, a1, rows):
        self.writes.append((tab, a1, rows))
        self.data[tab].extend([
            [r[0], (date(1899, 12, 30) + timedelta(days=r[1])).strftime("%d/%m/%Y"), *r[2:]]
            for r in rows
        ])


class CampaignTest(unittest.TestCase):
    def test_confirmed_batch_records_once_and_changes_next_selection(self):
        sheet = FakeSheet()
        self.assertEqual([x.group_id for x in top_groups(sheet)], ["G0001", "G0002"])
        ids = record_confirmed_batch(sheet, [
            {"group_id": "G0001", "sent_at": "2026-10-11T18:10:00+02:00", "evidence": "confirmación en WhatsApp"},
            {"group_id": "G0002", "sent_at": "2026-10-11T18:14:00+02:00", "evidence": "confirmación en WhatsApp"},
        ])
        self.assertEqual(ids, ["G0001", "G0002"])
        self.assertEqual(len(sheet.writes), 1)
        self.assertEqual([r[3] for r in sheet.writes[0][2]], ids)
        self.assertEqual(recommendations(sheet.data["Grupos"], sheet.data["Historial"], today=date(2026, 10, 12)), [])
        with self.assertRaisesRegex(ValueError, "Ya hay un envío"):
            record_confirmed_batch(sheet, [
                {"group_id": "G0001", "sent_at": "2026-10-11T19:00:00+02:00", "evidence": "confirmación"},
            ])
        self.assertEqual(len(sheet.writes), 1)

    def test_invalid_later_confirmation_keeps_batch_unwritten(self):
        sheet = FakeSheet()
        with self.assertRaisesRegex(ValueError, "Falta evidencia"):
            record_confirmed_batch(sheet, [
                {"group_id": "G0001", "sent_at": "2026-10-11T18:10:00+02:00", "evidence": "confirmación"},
                {"group_id": "G0002", "sent_at": "2026-10-11T18:12:00+02:00"},
            ])
        self.assertEqual(sheet.writes, [])


if __name__ == "__main__":
    unittest.main()
