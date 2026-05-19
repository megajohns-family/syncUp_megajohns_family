"""
Tests for app.models — Task, TaskList, TaskManager, UserManager, and
load_task_manager. Firestore is mocked out so no network is needed.
"""
import unittest
from unittest.mock import MagicMock, patch

from tests.conftest import *  # noqa: F401,F403

from app.models import (
    ColorTags,
    Task,
    TaskList,
    TaskManager,
    User,
    UserLogin,
    UserPasswordChange,
    UserDelete,
    UserManager,
    load_task_manager,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(**kwargs) -> TaskManager:
    """Return a TaskManager whose _save is a no-op mock."""
    with patch("app.models.save_to_firestore"):
        tm = TaskManager(**kwargs)
    tm._save = MagicMock()
    return tm


# ---------------------------------------------------------------------------
# ColorTags
# ---------------------------------------------------------------------------

class TestColorTags(unittest.TestCase):
    def test_values_are_strings(self):
        for tag in ColorTags:
            self.assertIsInstance(tag.value, str)

    def test_members(self):
        self.assertEqual(
            {t.value for t in ColorTags},
            {"NOTHING", "GREEN", "RED", "YELLOW", "BLUE", "PURPLE"},
        )


# ---------------------------------------------------------------------------
# Task / TaskList
# ---------------------------------------------------------------------------

class TestTask(unittest.TestCase):
    def test_defaults(self):
        t = Task(name="Buy milk")
        self.assertEqual(t.description, "")
        self.assertEqual(t.color_tag, ColorTags.NOTHING)
        self.assertIsNone(t.due_date)

    def test_custom_fields(self):
        t = Task(
            name="Write tests",
            description="unit tests",
            color_tag=ColorTags.GREEN,
            due_date="2026-12-31",
        )
        self.assertEqual(t.name, "Write tests")
        self.assertEqual(t.description, "unit tests")
        self.assertEqual(t.color_tag, ColorTags.GREEN)
        self.assertEqual(t.due_date, "2026-12-31")


class TestTaskList(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(TaskList(name="My list").task_ids, [])

    def test_with_task_ids(self):
        self.assertEqual(TaskList(name="My list", task_ids=[1, 2, 3]).task_ids, [1, 2, 3])


# ---------------------------------------------------------------------------
# TaskManager: lists
# ---------------------------------------------------------------------------

class TestTaskManagerLists(unittest.TestCase):
    def setUp(self):
        self.tm = _make_manager()

    def test_add_list_returns_id(self):
        self.assertEqual(self.tm.add_list("Work"), 1)

    def test_add_list_increments_id(self):
        self.assertNotEqual(self.tm.add_list("Work"), self.tm.add_list("Personal"))

    def test_add_list_appends_to_order(self):
        lid1 = self.tm.add_list("A")
        lid2 = self.tm.add_list("B")
        self.assertEqual(self.tm.list_order, [lid1, lid2])

    def test_add_list_saves(self):
        self.tm.add_list("Work")
        self.tm._save.assert_called()

    def test_remove_list_success(self):
        lid = self.tm.add_list("Work")
        self.assertTrue(self.tm.remove_list(lid))
        self.assertNotIn(lid, self.tm.lists)
        self.assertNotIn(lid, self.tm.list_order)

    def test_remove_list_missing(self):
        self.assertFalse(self.tm.remove_list(999))

    def test_remove_list_also_removes_tasks(self):
        lid = self.tm.add_list("Work")
        tid = self.tm.add_task(lid, "Task A")
        self.tm.remove_list(lid)
        self.assertNotIn(tid, self.tm.tasks)

    def test_rename_list_success(self):
        lid = self.tm.add_list("Old")
        self.assertTrue(self.tm.rename_list(lid, "New"))
        self.assertEqual(self.tm.lists[lid].name, "New")

    def test_rename_list_missing(self):
        self.assertFalse(self.tm.rename_list(999, "New"))

    def test_reorder_lists_success(self):
        lid1 = self.tm.add_list("A")
        lid2 = self.tm.add_list("B")
        self.assertTrue(self.tm.reorder_lists([lid2, lid1]))
        self.assertEqual(self.tm.list_order, [lid2, lid1])

    def test_reorder_lists_wrong_ids(self):
        self.tm.add_list("A")
        self.assertFalse(self.tm.reorder_lists([999]))


# ---------------------------------------------------------------------------
# TaskManager: tasks
# ---------------------------------------------------------------------------

class TestTaskManagerTasks(unittest.TestCase):
    def setUp(self):
        self.tm = _make_manager()
        self.lid = self.tm.add_list("Default")

    def test_add_task_returns_id(self):
        self.assertIsNotNone(self.tm.add_task(self.lid, "Task A"))

    def test_add_task_invalid_list_returns_none(self):
        self.assertIsNone(self.tm.add_task(999, "Task A"))

    def test_add_task_increments_id(self):
        self.assertNotEqual(
            self.tm.add_task(self.lid, "A"),
            self.tm.add_task(self.lid, "B"),
        )

    def test_add_task_attached_to_list(self):
        tid = self.tm.add_task(self.lid, "A")
        self.assertIn(tid, self.tm.lists[self.lid].task_ids)

    def test_add_task_with_due_date(self):
        tid = self.tm.add_task(self.lid, "A", "desc", "2027-01-15")
        self.assertEqual(self.tm.tasks[tid].due_date, "2027-01-15")

    def test_add_task_without_due_date_defaults_to_none(self):
        tid = self.tm.add_task(self.lid, "A")
        self.assertIsNone(self.tm.tasks[tid].due_date)

    def test_remove_task_success(self):
        tid = self.tm.add_task(self.lid, "A")
        self.assertTrue(self.tm.remove_task(tid))
        self.assertNotIn(tid, self.tm.tasks)
        self.assertNotIn(tid, self.tm.lists[self.lid].task_ids)

    def test_remove_task_missing(self):
        self.assertFalse(self.tm.remove_task(999))

    def test_change_task_name_success(self):
        tid = self.tm.add_task(self.lid, "Old")
        self.assertTrue(self.tm.change_task_name(tid, "New"))
        self.assertEqual(self.tm.tasks[tid].name, "New")

    def test_change_task_name_missing(self):
        self.assertFalse(self.tm.change_task_name(999, "New"))

    def test_change_task_description_success(self):
        tid = self.tm.add_task(self.lid, "A")
        self.assertTrue(self.tm.change_task_description(tid, "desc"))
        self.assertEqual(self.tm.tasks[tid].description, "desc")

    def test_change_task_description_missing(self):
        self.assertFalse(self.tm.change_task_description(999, "desc"))

    def test_change_color_tag_success(self):
        tid = self.tm.add_task(self.lid, "A")
        self.assertTrue(self.tm.change_color_tag(tid, ColorTags.RED))
        self.assertEqual(self.tm.tasks[tid].color_tag, ColorTags.RED)

    def test_change_color_tag_missing_task(self):
        self.assertFalse(self.tm.change_color_tag(999, ColorTags.RED))

    def test_change_due_date_success(self):
        tid = self.tm.add_task(self.lid, "A")
        self.assertTrue(self.tm.change_due_date(tid, "2027-01-15"))
        self.assertEqual(self.tm.tasks[tid].due_date, "2027-01-15")

    def test_change_due_date_clear(self):
        tid = self.tm.add_task(self.lid, "A")
        self.tm.change_due_date(tid, "2027-01-15")
        self.assertTrue(self.tm.change_due_date(tid, None))
        self.assertIsNone(self.tm.tasks[tid].due_date)

    def test_change_due_date_missing_task(self):
        self.assertFalse(self.tm.change_due_date(999, "2027-01-15"))

    def test_move_task_success(self):
        lid2 = self.tm.add_list("Other")
        tid = self.tm.add_task(self.lid, "Task")
        self.assertTrue(self.tm.move_task(tid, lid2))
        self.assertIn(tid, self.tm.lists[lid2].task_ids)
        self.assertNotIn(tid, self.tm.lists[self.lid].task_ids)

    def test_move_task_same_list_is_noop(self):
        tid = self.tm.add_task(self.lid, "Task")
        self.assertTrue(self.tm.move_task(tid, self.lid))
        self.assertIn(tid, self.tm.lists[self.lid].task_ids)

    def test_move_task_invalid_task(self):
        self.assertFalse(self.tm.move_task(999, self.lid))

    def test_move_task_invalid_target_list(self):
        tid = self.tm.add_task(self.lid, "Task")
        self.assertFalse(self.tm.move_task(tid, 999))

    def test_get_list_tasks(self):
        tid = self.tm.add_task(self.lid, "A")
        tasks = self.tm.get_list_tasks(self.lid)
        self.assertIn(tid, tasks)

    def test_get_list_tasks_invalid_list(self):
        self.assertIsNone(self.tm.get_list_tasks(999))

    def test_find_list_of_task(self):
        tid = self.tm.add_task(self.lid, "A")
        self.assertEqual(self.tm._find_list_of_task(tid), self.lid)

    def test_find_list_of_task_missing(self):
        self.assertIsNone(self.tm._find_list_of_task(999))


# ---------------------------------------------------------------------------
# TaskManager: batching, ordering, counters
# ---------------------------------------------------------------------------

class TestTaskManagerBatch(unittest.TestCase):
    def test_batch_defers_save_until_end(self):
        with patch("app.models.save_to_firestore") as mock_save:
            tm = TaskManager()
            tm.begin_batch()
            lid = tm.add_list("A")
            tm.add_task(lid, "T")
            mock_save.assert_not_called()
            tm.end_batch()
            mock_save.assert_called_once()

    def test_end_batch_with_no_changes_does_not_save(self):
        with patch("app.models.save_to_firestore") as mock_save:
            tm = TaskManager()
            tm.begin_batch()
            tm.end_batch()
            mock_save.assert_not_called()


class TestTaskManagerGetAll(unittest.TestCase):
    def test_get_all_respects_order(self):
        tm = _make_manager()
        lid1 = tm.add_list("First")
        lid2 = tm.add_list("Second")
        tm.reorder_lists([lid2, lid1])
        self.assertEqual(list(tm.get_all().keys()), [lid2, lid1])

    def test_get_all_includes_task_payload(self):
        tm = _make_manager()
        lid = tm.add_list("L")
        tid = tm.add_task(lid, "Hello")
        result = tm.get_all()
        self.assertEqual(result[lid]["name"], "L")
        self.assertIn(tid, result[lid]["tasks"])


class TestTaskManagerCounterInit(unittest.TestCase):
    def test_counters_resume_from_existing_data(self):
        tm = _make_manager(
            lists={3: TaskList(name="Existing")},
            tasks={5: Task(name="Old task")},
        )
        self.assertEqual(tm._next_list_id, 4)
        self.assertEqual(tm._next_task_id, 6)

    def test_list_order_includes_missing_lists(self):
        tm = _make_manager(
            lists={1: TaskList(name="A"), 2: TaskList(name="B")},
            list_order=[1],
        )
        self.assertEqual(set(tm.list_order), {1, 2})

    def test_list_order_drops_unknown_ids(self):
        tm = _make_manager(
            lists={1: TaskList(name="A")},
            list_order=[1, 99],
        )
        self.assertEqual(tm.list_order, [1])


# ---------------------------------------------------------------------------
# Pydantic user-input schemas
# ---------------------------------------------------------------------------

class TestUserModels(unittest.TestCase):
    def test_user(self):
        u = User(login="alice", password="pw")
        self.assertEqual(u.login, "alice")
        self.assertEqual(u.password, "pw")

    def test_user_login(self):
        self.assertEqual(UserLogin(login="alice", password="pw").login, "alice")

    def test_user_password_change(self):
        upc = UserPasswordChange(login="alice", old_password="old", new_password="new")
        self.assertEqual(upc.new_password, "new")

    def test_user_delete(self):
        self.assertEqual(UserDelete(login="alice", password="pw").login, "alice")


# ---------------------------------------------------------------------------
# UserManager
# ---------------------------------------------------------------------------

class TestUserManager(unittest.TestCase):
    """All Firestore calls are stubbed; only the in-memory dict is exercised."""

    def _make_um(self, existing_users: dict | None = None) -> UserManager:
        um = UserManager()
        um.users = existing_users or {}
        um._reload = MagicMock(side_effect=lambda: None)
        um._save = MagicMock()
        return um

    # ---- register ----
    def test_register_new_user(self):
        um = self._make_um()
        self.assertTrue(um.register_user("alice", "password1"))
        self.assertIn("alice", um.users)

    def test_register_stores_hashed_password(self):
        um = self._make_um()
        um.register_user("alice", "password1")
        self.assertNotEqual(um.users["alice"], "password1")

    def test_register_duplicate_user(self):
        um = self._make_um({"alice": "somehash"})
        self.assertFalse(um.register_user("alice", "password1"))

    def test_register_saves(self):
        um = self._make_um()
        um.register_user("bob", "pw")
        um._save.assert_called_once()

    # ---- login ----
    def test_login_correct_password(self):
        from app.hash import hash_password
        um = self._make_um({"alice": hash_password("correct")})
        self.assertTrue(um.login_user("alice", "correct"))

    def test_login_wrong_password(self):
        from app.hash import hash_password
        um = self._make_um({"alice": hash_password("correct")})
        self.assertFalse(um.login_user("alice", "wrong"))

    def test_login_unknown_user(self):
        um = self._make_um()
        self.assertFalse(um.login_user("ghost", "pw"))

    # ---- change_password ----
    def test_change_password_success(self):
        from app.hash import hash_password, verify_password
        um = self._make_um({"alice": hash_password("old")})
        self.assertTrue(um.change_password("alice", "old", "new"))
        self.assertTrue(verify_password("new", um.users["alice"]))

    def test_change_password_wrong_old(self):
        from app.hash import hash_password
        um = self._make_um({"alice": hash_password("old")})
        self.assertFalse(um.change_password("alice", "wrong", "new"))

    def test_change_password_unknown_user(self):
        um = self._make_um()
        self.assertFalse(um.change_password("ghost", "old", "new"))

    # ---- delete_account ----
    def test_delete_account_success(self):
        from app.hash import hash_password
        um = self._make_um({"alice": hash_password("pw")})
        self.assertTrue(um.delete_account("alice", "pw"))
        self.assertNotIn("alice", um.users)

    def test_delete_account_wrong_password(self):
        from app.hash import hash_password
        um = self._make_um({"alice": hash_password("pw")})
        self.assertFalse(um.delete_account("alice", "wrong"))
        self.assertIn("alice", um.users)

    def test_delete_account_unknown_user(self):
        um = self._make_um()
        self.assertFalse(um.delete_account("ghost", "pw"))


# ---------------------------------------------------------------------------
# load_task_manager
# ---------------------------------------------------------------------------

class TestLoadTaskManager(unittest.TestCase):
    def test_returns_empty_manager_when_not_found(self):
        with patch("app.models.load_from_firestore_raw", return_value=None):
            tm = load_task_manager("nope")
            self.assertIsInstance(tm, TaskManager)
            self.assertEqual(tm.board_id, "nope")
            self.assertEqual(tm.lists, {})
            self.assertEqual(tm.tasks, {})

    def test_loads_and_coerces_string_keys_to_int(self):
        data = {
            "name": "Sprint",
            "owner": "alice",
            "users": [],
            "lists": {"1": {"name": "Todo", "task_ids": ["7"]}},
            "tasks": {"7": {"name": "Item", "description": "", "color_tag": "GREEN"}},
            "list_order": ["1"],
        }
        with patch("app.models.load_from_firestore_raw", return_value=data):
            tm = load_task_manager("brd")
            self.assertEqual(tm.board_id, "brd")
            self.assertIn(1, tm.lists)
            self.assertIn(7, tm.tasks)
            self.assertEqual(tm.lists[1].task_ids, [7])
            self.assertEqual(tm.list_order, [1])
            self.assertEqual(tm.tasks[7].color_tag, ColorTags.GREEN)

    def test_legacy_int_color_tag_is_remapped(self):
        data = {
            "name": "B",
            "lists": {"1": {"name": "L", "task_ids": ["1"]}},
            "tasks": {"1": {"name": "T", "description": "", "color_tag": 3}},
            "list_order": ["1"],
        }
        with patch("app.models.load_from_firestore_raw", return_value=data):
            tm = load_task_manager("brd")
            # mapping 3 -> "RED"
            self.assertEqual(tm.tasks[1].color_tag, ColorTags.RED)

    def test_legacy_unknown_int_color_falls_back_to_nothing(self):
        data = {
            "name": "B",
            "lists": {"1": {"name": "L", "task_ids": ["1"]}},
            "tasks": {"1": {"name": "T", "description": "", "color_tag": 999}},
            "list_order": ["1"],
        }
        with patch("app.models.load_from_firestore_raw", return_value=data):
            tm = load_task_manager("brd")
            self.assertEqual(tm.tasks[1].color_tag, ColorTags.NOTHING)


if __name__ == "__main__":
    unittest.main()
