import unittest
from types import SimpleNamespace
from unittest.mock import patch

from main import Game
from objects import Flea, Gate, Rat
from quest import QuestManager, recovery_ending
from settings import (HIGH_SPREAD_THRESHOLD, REMOVAL_FAILURE_THRESHOLD,
                      REMOVAL_FAILURE_SPREAD_GAIN, SPREAD_INTERVAL,
                      STATE_DIALOGUE, STATE_ENDING, STATE_MENU, STATE_PLAYING)
from stats import PlagueStats


class DummyTouch:
    def release(self):
        pass

    def move_vector(self):
        return (0, 0)


class DummyPlayer:
    rect = SimpleNamespace()

    def update(self, dt, obstacles, movement):
        pass


class FlagObject:
    def __init__(self):
        self.investigated = True
        self.discovered = True
        self.removed = True
        self.cleaned = True


def make_game(chapter, spread):
    game = Game.__new__(Game)
    game.state = STATE_PLAYING
    game.quest = QuestManager()
    game.quest.go_to(chapter)
    game.investigation_reward_pending = False
    game.stats = PlagueStats()
    game.stats.values["spread"] = spread
    game.objects = []
    game.npcs = []
    game.nearby = None
    game.toast = None
    game.dialogue = None
    game.touch = DummyTouch()
    game.time = 0.0
    game.player = DummyPlayer()
    game.world = SimpleNamespace(walls=[])
    game.obstacles = lambda *exclude: []
    game.update_camera = lambda: None
    game.find_nearby = lambda: None
    return game


def finish_current_quest(game):
    game.quest.counts = [goal["count"] for goal in game.quest.goals]
    game.check_quest()


class InfectionProgressionTests(unittest.TestCase):
    def test_chapter_three_requires_rats_and_fleas_separately(self):
        quest = QuestManager()
        quest.go_to(3)

        self.assertEqual([goal["event"] for goal in quest.goals], ["rat", "flea"])
        for index in range(6):
            quest.notify("rat", f"rat_{index}")
        self.assertFalse(quest.is_complete())
        for index in range(10):
            quest.notify("flea", f"flea_{index}")
        self.assertTrue(quest.is_complete())

    def test_chapter_three_animals_pour_out_after_gate_investigation(self):
        quest = QuestManager()
        quest.go_to(3)
        with patch("objects.load_image", return_value=None):
            rats = [Rat({"id": f"rat_{index}", "tile": (18, 1)})
                    for index in range(6)]
            fleas = [Flea({"id": f"flea_{index}", "tile": (18, 1)})
                     for index in range(10)]
            gate = Gate({"id": "gate_west", "tile": (0, 14),
                         "orient": "v", "name": "서쪽 성문"})
        game = SimpleNamespace(quest=quest, objects=[*rats, *fleas, gate],
                               pending_dialogue_action=None)

        self.assertFalse(any(animal.visible(game) for animal in [*rats, *fleas]))
        lines = gate.interact(game)

        self.assertFalse(any(animal.visible(game) for animal in [*rats, *fleas]))
        self.assertIn("확인해 본다", lines[0][1])
        follow_lines = game.pending_dialogue_action()
        self.assertTrue(all(animal.visible(game) for animal in [*rats, *fleas]))
        self.assertTrue(all(animal.rect.centerx > gate.rect.centerx
                            for animal in [*rats, *fleas]))
        self.assertGreater(len({animal.rect.center for animal in [*rats, *fleas]}), 12)
        self.assertIn("쏟아져", follow_lines[0][1])
        self.assertFalse(gate.can_interact(game))

    def test_low_spread_skips_investigation_then_succeeds(self):
        game = make_game(6, HIGH_SPREAD_THRESHOLD + 9)
        finish_current_quest(game)
        self.assertEqual(game.quest.index, 8)
        self.assertIn("마지막 감염원", game.quest.chapter["name"])

        game.state = STATE_PLAYING
        finish_current_quest(game)
        self.assertEqual(game.quest.index, 9)
        self.assertIn("마을 회복", game.quest.chapter["name"])

    def test_high_spread_investigates_then_succeeds(self):
        game = make_game(6, HIGH_SPREAD_THRESHOLD + 10)
        finish_current_quest(game)
        self.assertEqual(game.quest.index, 7)

        game.state = STATE_PLAYING
        finish_current_quest(game)
        self.assertEqual(game.quest.index, 8)
        game.state = STATE_PLAYING
        game.stats.values["spread"] = REMOVAL_FAILURE_THRESHOLD - 1
        finish_current_quest(game)
        self.assertEqual(game.quest.index, 9)

    def test_failure_increases_spread_returns_to_seven_and_resets(self):
        game = make_game(8, REMOVAL_FAILURE_THRESHOLD)
        flag = FlagObject()
        game.objects = [flag]
        finish_current_quest(game)

        self.assertEqual(game.quest.index, 7)
        self.assertEqual(game.stats["spread"],
                         REMOVAL_FAILURE_THRESHOLD + REMOVAL_FAILURE_SPREAD_GAIN)
        self.assertEqual(game.quest.counts, [0])
        self.assertFalse(flag.investigated)
        self.assertFalse(flag.discovered)
        self.assertFalse(flag.removed)
        self.assertFalse(flag.cleaned)
        self.assertEqual(game.state, STATE_DIALOGUE)

    def test_failure_rolls_back_investigation_reward(self):
        game = make_game(7, HIGH_SPREAD_THRESHOLD)
        trust_before = game.stats["trust"]
        finish_current_quest(game)
        self.assertEqual(game.stats["trust"], trust_before + 5)

        game.state = STATE_PLAYING
        game.stats.values["spread"] = REMOVAL_FAILURE_THRESHOLD
        finish_current_quest(game)
        self.assertEqual(game.stats["trust"], trust_before)
        self.assertFalse(game.investigation_reward_pending)

    def test_failure_reaching_100_starts_bad_ending(self):
        game = make_game(8, 100 - REMOVAL_FAILURE_SPREAD_GAIN)
        finish_current_quest(game)
        self.assertEqual(game.stats["spread"], 100)
        self.assertEqual(game.state, STATE_ENDING)
        self.assertEqual(game.ending["title"], "배드 엔딩: 검은 죽음")

    def test_spread_advances_during_infection_dialogue_and_play(self):
        game = make_game(7, HIGH_SPREAD_THRESHOLD)
        game.state = STATE_DIALOGUE
        game.update(SPREAD_INTERVAL)
        self.assertEqual(game.stats["spread"], HIGH_SPREAD_THRESHOLD + 1)

        game.state = STATE_PLAYING
        game.update(SPREAD_INTERVAL)
        self.assertEqual(game.stats["spread"], HIGH_SPREAD_THRESHOLD + 2)

    def test_menu_pauses_spread(self):
        game = make_game(7, HIGH_SPREAD_THRESHOLD)
        game.state = STATE_MENU
        game.update(SPREAD_INTERVAL * 2)
        self.assertEqual(game.stats["spread"], HIGH_SPREAD_THRESHOLD)

    def test_chapters_one_to_six_keep_default_sequential_transition(self):
        quest = QuestManager()
        for chapter in range(1, 6):
            quest.go_to(chapter)
            quest.counts = [goal["count"] for goal in quest.goals]
            quest.complete()
            self.assertEqual(quest.index, chapter + 1)

    def test_recovery_and_ending_rules_are_unchanged(self):
        stats = PlagueStats()
        stats.values.update(spread=10, trust=20, survivors=100)
        self.assertEqual(recovery_ending(stats), "return")
        stats.values["spread"] = 11
        self.assertIsNone(recovery_ending(stats))

    def test_recovery_does_not_end_before_treatment(self):
        game = make_game(9, 10)

        game.check_quest()

        self.assertEqual(game.state, STATE_PLAYING)

    def test_recovery_ends_after_treatment_goal_is_complete(self):
        game = make_game(9, 10)
        game.quest.notify("recovery", "village_clinic_part9")

        game.check_quest()

        self.assertEqual(game.state, STATE_ENDING)
        self.assertEqual(game.ending["title"], "일반 귀환")

    def test_recovery_clinic_can_finish_when_entry_spread_is_already_low(self):
        from objects import RecoveryClinic

        game = make_game(9, 10)
        clinic = RecoveryClinic({"id": "village_clinic_part9", "tile": (5, 12)})

        self.assertTrue(clinic.can_interact(game))
        clinic.interact(game)

        self.assertTrue(clinic.finished)
        self.assertEqual(game.state, STATE_ENDING)


if __name__ == "__main__":
    unittest.main()
