import unittest
from unittest.mock import patch, MagicMock
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
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(**kwargs) -> TaskManager:
    """Return a TaskManager with _save patched out."""
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
        expected = {"NOTHING", "GREEN", "RED", "YELLOW", "BLUE", "PURPLE"}
        self.assertEqual({t.value for t in ColorTags}, expected)


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class TestTask(unittest.TestCase):
    def test_defaults(self):
        t = Task(name="Buy milk")
        self.assertEqual(t.description, "")
        self.assertEqual(t.color_tag, ColorTags.NOTHING)

    def test_custom_fields(self):
        t = Task(name="Write tests", description="unit tests", color_tag=ColorTags.GREEN)
        self.assertEqual(t.name, "Write tests")
        self.assertEqual(t.description, "unit tests")
        self.assertEqual(t.color_tag, ColorTags.GREEN)


# ---------------------------------------------------------------------------
# TaskList
# ---------------------------------------------------------------------------

class TestTaskList(unittest.TestCase):
    def test_defaults(self):
        tl = TaskList(name="My list")
        self.assertEqual(tl.task_ids, [])

    def test_with_task_ids(self):
        tl = TaskList(name="My list", task_ids=[1, 2, 3])
        self.assertEqual(tl.task_ids, [1, 2, 3])


# ---------------------------------------------------------------------------
# TaskManager
# ---------------------------------------------------------------------------

class TestTaskManagerLists(unittest.TestCase):
    def setUp(self):
        self.tm = _make_manager()

    def test_add_list_returns_id(self):
        lid = self.tm.add_list("Work")
        self.assertEqual(lid, 1)

    def test_add_list_increments_id(self):
        lid1 = self.tm.add_list("Work")
        lid2 = self.tm.add_list("Personal")
        self.assertNotEqual(lid1, lid2)

    def test_add_list_saves(self):
        self.tm.add_list("Work")
        self.tm._save.assert_called()

    def test_remove_list_success(self):
        lid = self.tm.add_list("Work")
        result = self.tm.remove_list(lid)
        self.assertTrue(result)
        self.assertNotIn(lid, self.tm.lists)

    def test_remove_list_missing(self):
        self.assertFalse(self.tm.remove_list(999))

    def test_remove_list_also_removes_tasks(self):
        lid = self.tm.add_list("Work")
        tid = self.tm.add_task(lid, "Task A")
        self.tm.remove_list(lid)
        self.assertNotIn(tid, self.tm.tasks)

    def test_rename_list_success(self):
        lid = self.tm.add_list("Old")
        result = self.tm.rename_list(lid, "New")
        self.assertTrue(result)
        self.assertEqual(self.tm.lists[lid].name, "New")

    def test_rename_list_missing(self):
        self.assertFalse(self.tm.rename_list(999, "New"))

    def test_reorder_lists_success(self):
        lid1 = self.tm.add_list("A")
        lid2 = self.tm.add_list("B")
        result = self.tm.reorder_lists([lid2, lid1])
        self.assertTrue(result)
        self.assertEqual(self.tm.list_order, [lid2, lid1])

    def test_reorder_lists_wrong_ids(self):
        self.tm.add_list("A")
        self.assertFalse(self.tm.reorder_lists([999]))

    def test_get_lists(self):
        lid = self.tm.add_list("X")
        self.assertIn(lid, self.tm.get_lists())

    def test_get_listid_by_name_found(self):
        lid = self.tm.add_list("MyList")
        self.assertEqual(self.tm.get_listid_by_name("MyList"), lid)

    def test_get_listid_by_name_not_found(self):
        self.assertIsNone(self.tm.get_listid_by_name("Ghost"))


class TestTaskManagerTasks(unittest.TestCase):
    def setUp(self):
        self.tm = _make_manager()
        self.lid = self.tm.add_list("Default")

    def test_add_task_returns_id(self):
        tid = self.tm.add_task(self.lid, "Task A")
        self.assertIsNotNone(tid)

    def test_add_task_invalid_list(self):
        self.assertIsNone(self.tm.add_task(999, "Task A"))

    def test_add_task_increments_id(self):
        tid1 = self.tm.add_task(self.lid, "A")
        tid2 = self.tm.add_task(self.lid, "B")
        self.assertNotEqual(tid1, tid2)

    def test_remove_task_success(self):
        tid = self.tm.add_task(self.lid, "A")
        self.assertTrue(self.tm.remove_task(tid))
        self.assertNotIn(tid, self.tm.tasks)

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

    def test_move_task_success(self):
        lid2 = self.tm.add_list("Other")
        tid = self.tm.add_task(self.lid, "Task")
        self.assertTrue(self.tm.move_task(tid, lid2))
        self.assertIn(tid, self.tm.lists[lid2].task_ids)
        self.assertNotIn(tid, self.tm.lists[self.lid].task_ids)

    def test_move_task_same_list(self):
        tid = self.tm.add_task(self.lid, "Task")
        self.assertTrue(self.tm.move_task(tid, self.lid))

    def test_move_task_invalid_task(self):
        self.assertFalse(self.tm.move_task(999, self.lid))

    def test_move_task_invalid_list(self):
        tid = self.tm.add_task(self.lid, "Task")
        self.assertFalse(self.tm.move_task(tid, 999))

    def test_get_list_tasks(self):
        tid = self.tm.add_task(self.lid, "A")
        tasks = self.tm.get_list_tasks(self.lid)
        self.assertIn(tid, tasks)

    def test_get_list_tasks_invalid_list(self):
        self.assertIsNone(self.tm.get_list_tasks(999))


class TestTaskManagerColorTags(unittest.TestCase):
    def setUp(self):
        self.tm = _make_manager()
        self.lid = self.tm.add_list("Default")
        self.tid = self.tm.add_task(self.lid, "Task")

    def test_add_color_tag_success(self):
        self.assertTrue(self.tm.add_color_tag(self.tid, ColorTags.GREEN))
        self.assertEqual(self.tm.tasks[self.tid].color_tag, ColorTags.GREEN)

    def test_add_color_tag_already_set(self):
        self.tm.add_color_tag(self.tid, ColorTags.GREEN)
        self.assertFalse(self.tm.add_color_tag(self.tid, ColorTags.RED))

    def test_add_color_tag_missing_task(self):
        self.assertFalse(self.tm.add_color_tag(999, ColorTags.GREEN))

    def test_remove_color_tag_success(self):
        self.tm.add_color_tag(self.tid, ColorTags.BLUE)
        self.tm.remove_color_tag(self.tid)
        self.assertEqual(self.tm.tasks[self.tid].color_tag, ColorTags.NOTHING)

    def test_remove_color_tag_already_nothing(self):
        self.assertFalse(self.tm.remove_color_tag(self.tid))

    def test_remove_color_tag_missing_task(self):
        self.assertFalse(self.tm.remove_color_tag(999))

    def test_change_color_tag_success(self):
        self.assertTrue(self.tm.change_color_tag(self.tid, ColorTags.RED))
        self.assertEqual(self.tm.tasks[self.tid].color_tag, ColorTags.RED)

    def test_change_color_tag_missing_task(self):
        self.assertFalse(self.tm.change_color_tag(999, ColorTags.RED))


class TestTaskManagerBatch(unittest.TestCase):
    def test_batch_defers_save_until_end(self):
        with patch("app.models.save_to_firestore") as mock_save:
            tm = TaskManager()
            tm.begin_batch()
            lid = tm.add_list("A")
            tm.add_task(lid, "T")
            # save_to_firestore must not have been called yet
            mock_save.assert_not_called()
            tm.end_batch()
            # After end_batch exactly one save occurs
            mock_save.assert_called_once()

    def test_end_batch_no_dirty(self):
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
        keys = list(tm.get_all().keys())
        self.assertEqual(keys, [lid2, lid1])


class TestTaskManagerCounterInit(unittest.TestCase):
    def test_counters_resume_from_existing_data(self):
        """_init_counters should set next IDs above existing keys."""
        tm = _make_manager(
            lists={3: TaskList(name="Existing")},
            tasks={5: Task(name="Old task")},
        )
        self.assertEqual(tm._next_list_id, 4)
        self.assertEqual(tm._next_task_id, 6)


# ---------------------------------------------------------------------------
# Pydantic user models
# ---------------------------------------------------------------------------

class TestUserModels(unittest.TestCase):
    def test_user_fields(self):
        u = User(login="alice", password="pw")
        self.assertEqual(u.login, "alice")
        self.assertEqual(u.password, "pw")

    def test_user_login_fields(self):
        ul = UserLogin(login="alice", password="pw")
        self.assertEqual(ul.login, "alice")

    def test_user_password_change_fields(self):
        upc = UserPasswordChange(login="alice", old_password="old", new_password="new")
        self.assertEqual(upc.new_password, "new")

    def test_user_delete_fields(self):
        ud = UserDelete(login="alice", password="pw")
        self.assertEqual(ud.login, "alice")


# ---------------------------------------------------------------------------
# UserManager
# ---------------------------------------------------------------------------

class TestUserManager(unittest.TestCase):
    """Tests for UserManager with Firestore fully mocked."""

    def _make_um(self, existing_users: dict | None = None) -> UserManager:
        """Return a UserManager whose Firestore calls are stubbed."""
        um = UserManager()
        um.users = existing_users or {}
        um._reload = MagicMock(side_effect=lambda: None)  # no-op reload
        um._save = MagicMock()
        return um

    # register_user
    def test_register_new_user(self):
        um = self._make_um()
        self.assertTrue(um.register_user("alice", "password1"))
        self.assertIn("alice", um.users)

    def test_register_duplicate_user(self):
        um = self._make_um({"alice": "somehash"})
        self.assertFalse(um.register_user("alice", "password1"))

    def test_register_saves(self):
        um = self._make_um()
        um.register_user("bob", "pw")
        um._save.assert_called_once()

    # login_user
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

    # change_password
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

    # delete_account
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


if __name__ == "__main__":
    unittest.main()
