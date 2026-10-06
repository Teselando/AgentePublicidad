import unittest
from datetime import date

from agente_mariii.core import recommendations, next_send_date
from agente_mariii.discovery import canonical_invite


def group(id_, name, family="", confidence="Desconocida", priority="Media", state="Disponible"):
    return [id_, name, family, confidence, "No", "", "", "", "0", priority, state]


def sent(day, id_, family=""):
    return ["E0001", day, "", id_, family]


class RulesTest(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 10, 6)

    def test_group_cooldown_is_30_days(self):
        groups = [group("G1", "Ingeniería Informática")]
        history = [sent("06/09/2026", "G1")]
        self.assertEqual([c.group_id for c in recommendations(groups, history, today=self.today)], ["G1"])
        history = [sent("07/09/2026", "G1")]
        self.assertEqual(recommendations(groups, history, today=self.today), [])
        self.assertEqual(next_send_date(date(2026, 10, 5)), date(2026, 11, 4))

    def test_high_family_waits_seven_days(self):
        groups = [group("G2", "Arquitectura", "Red A", "Alta")]
        self.assertEqual(recommendations(groups, [sent("01/10/2026", "G1", "Red A")], today=self.today), [])
        self.assertEqual(len(recommendations(groups, [sent("29/09/2026", "G1", "Red A")], today=self.today)), 1)

    def test_medium_and_unknown_not_repeated_today(self):
        groups = [group("G2", "Ingeniería Industrial", "Red B", "Media"), group("G3", "Matemáticas")]
        history = [sent("06/10/2026", "G1", "Red B"), sent("06/10/2026", "G9")]
        self.assertEqual(recommendations(groups, history, today=self.today), [])
        history = [sent("05/10/2026", "G1", "Red B")]
        self.assertEqual([x.group_id for x in recommendations(groups, history, today=self.today)], ["G2", "G3"])

    def test_one_per_family_and_no_blocked_groups(self):
        groups = [group("G1", "Ingeniería A", "Red C", "Media"), group("G2", "Ingeniería B", "Red C", "Media"),
                  group("G3", "ADE", "", "Desconocida", state="Pausado")]
        self.assertEqual(len(recommendations(groups, [], today=self.today)), 1)

    def test_invite_normalization(self):
        code = "AbCdEf1234567890123456"
        self.assertEqual(canonical_invite(f"https:\\/\\/chat.whatsapp.com\\/{code}?src=x"), [f"https://chat.whatsapp.com/{code}"])


if __name__ == "__main__":
    unittest.main()
