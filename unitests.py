import unittest
from unittest.mock import patch
from app.models import TaskManager, UserManager, ColorTags
from app.hash import hash_password, verify_password

#blok zapisu do pliku i bazy danych

def patch_io(func):
    """Dekorator – wycisza save_to_json i push_to_db w każdym teście."""
    @patch("app.models.save_to_json")
    @patch("app.models.push_to_db")
    def wrapper(self, mock_push, mock_save, *args, **kwargs):
        return func(self, *args, **kwargs)
    return wrapper


#1 . tests for hash
class TestHash(unittest.TestCase):

    def test_hash_return_string(self):
        #it returns if hash has only string and no int , so no numbers
        result = hash_password("secretpassword")
        self.assertIsInstance(result, str)

    def test_hash_has_sol(self):
        """Format: sól$hash - it must be exactly one dollar"""
        result = hash_password("secretpassword")
        self.assertEqual(result.count("$"), 1)

    def test_two_hashes_of_the_same_password_are_different(self):
        """every call generates new sol"""
        pass1 = hash_password("password")
        pass2 = hash_password("password")
        self.assertNotEqual(pass1, pass2)

    def test_verify_correct_password(self):
        stored = hash_password("secret")
        self.assertTrue(verify_password("secret", stored))

    def test_verify_incorrect_password(self):
        stored = hash_password("secret")
        self.assertFalse(verify_password("differentword", stored))

    def test_verify_empty_string(self):
        stored = hash_password("secret")
        self.assertFalse(verify_password("", stored))

    def test_verify_wrong_format_stored(self):
        """incorrect format stored should not throw a exception – returns False."""
        self.assertFalse(verify_password("password", "this_is_not_correct_hash"))

#tests for task manager

class TestTaskManager(unittest.TestCase):

    def setUp(self):
        """Fresh TaskManager before every test , I/0 muted"""
        patcher_save = patch("app.models.save_to_json")
        patcher_push = patch("app.models.push_to_db")
        self.mock_save = patcher_save.start()
        self.mock_push = patcher_push.start()
        self.addCleanup(patcher_save.stop)
        self.addCleanup(patcher_push.stop)

        self.taskmanager= TaskManager()

    #lists

    def test_add_list_returns_id(self):
        listid = self.taskmanager.add_list("Todo")
        self.assertIsInstance(listid, int)

    def test_add_list_id_grows(self):
        list_id1 = self.taskmanager.add_list("list A")
        list_id2 = self.taskmanager.add_list("list B")
        self.assertGreater(list_id2, list_id1)

    def test_Add_list_appears_in_list(self):
        listid = self.taskmanager.add_list("work")
        self.assertIn(listid, self.taskmanager.lists)
        self.assertEqual(self.taskmanager.lists[listid].name, "work")

    def test_remove_list_existing(self):
        listid = self.taskmanager.add_list("removable")
        result = self.taskmanager.remove_list(listid)
        self.assertTrue(result)
        self.assertNotIn(listid, self.tm.lists)

    def test_remove_list_notexisting(self):
        result = self.taskmanager.remove_list(999)
        self.assertFalse(result)

    def test_remove_list_deletes_its_tasks(self):
        listid = self.tm.add_list("Lists with tasks")
        taskid = self.tm.add_task(listid, "Task to delete")
        self.tm.remove_list(listid)
        self.assertNotIn(taskid, self.taskmanager.tasks)

    def test_rename_list(self):
        listid = self.taskmanager.add_list("old name")
        result = self.taskmanager.rename_list(listid, "new name")
        self.assertTrue(result)
        self.assertEqual(self.taskmanager.lists[listid].name, "new name")

    def test_rename_list_nieistniejaca(self):
        result = self.tm.rename_list(999, "whatever")
        self.assertFalse(result)

    #tasks

    def test_add_task_returns_id(self):
        listid = self.taskmanager.add_list("List")
        taskid = self.taskmanager.add_task(listid, "My opinion")
        self.assertIsInstance(taskid, int)

    def test_add_task_appears_in_tasks(self):
        listid = self.taskmanager .add_list("List")
        taskid = self.taskmanager.add_task(listid, "task", "description")
        self.assertIn(taskid, self.taskmanager.tasks)
        self.assertEqual(self.taskmanager.tasks[taskid].name, "task")
        self.assertEqual(self.taskmanager.tasks[taskid].description, "description")

    def test_add_task_to_existing_task(self):
        result = self.taskmanager.add_task(999, "opinion")
        self.assertIsNone(result)

    def test_add_task_goes_to_the_list(self):
        listid = self.taskmanager.add_list("list")
        taskid = self.taskmanager.add_task(listid, "task")
        self.assertIn(taskid, self.tm.lists[listid].task_ids)

    def test_remove_task_which_exists(self):
        listid = self.taskmanager.add_list("list")
        taskid = self.taskmanager.add_task(listid, "task")
        result = self.taskmanager.remove_task(taskid)
        self.assertTrue(result)
        self.assertNotIn(taskid, self.tm.tasks)

    def test_remove_task_dissapear_from_list(self):
        listid = self.taskmanager.add_list("list")
        taskid = self.taskmanager.add_task(listid, "task")
        self.tm.remove_task(taskid)
        self.assertNotIn(taskid, self.taskmanager.lists[listid].task_ids)

    def test_remove_task_not_existing(self):
        result = self.taskmanager.remove_task(999)
        self.assertFalse(result)

    def test_change_task_name(self):
        listid = self.taskmanager.add_list("Lista")
        taskid = self.taskmanager.add_task(listid, "old name")
        result = self.taskmanager.change_task_name(taskid, "new name")
        self.assertTrue(result)
        self.assertEqual(self.taskmanager.tasks[taskid].name, "new name")

    def test_change_task_name_not_existing(self):
        result = self.taskmanager.change_task_name(999, "new name")
        self.assertFalse(result)

    def test_change_task_description(self):
        listid = self.taskmanager.add_list("list")
        taskid = self.taskmanager.add_task(listid, "task")
        result = self.taskmanager.change_task_description(taskid, "New description")
        self.assertTrue(result)
        self.assertEqual(self.taskmanager.tasks[taskid].description, "new description")

    def test_change_task_description_not_existing(self):
        result = self.taskmanager.change_task_description(999, "description")
        self.assertFalse(result)

    #moving tasks

    def test_move_tasks_to_another_list(self):
        list1 = self.taskmanager.add_list("list 1")
        list2 = self.taskmanager.add_list("list 2")
        taskid = self.taskmanager.add_task(list1, "task")
        result = self.taskmanager.move_task(taskid, list2)
        self.assertTrue(result)
        self.assertNotIn(taskid, self.taskmanager.lists[list1].task_ids)
        self.assertIn(taskid, self.taskmanager.lists[list2].task_ids)

    def test_move_task_the_same_list(self):
        listid = self.taskmanager.add_list("list")
        taskid = self.taskmanager.add_task(listid, "task")
        result = self.taskmanager.move_task(taskid, listid)
        self.assertTrue(result)
        self.assertIn(taskid, self.taskmanager.lists[listid].task_ids)

    def test_move_task_not_exisiting_task(self):
        listid = self.taskmanager.add_list("list")
        result = self.taskmanager.move_task(999, listid)
        self.assertFalse(result)

    def test_move_task_to_not_existing_list(self):
        listid = self.taskmanager.add_list("list")
        taskid = self.taskmanager.add_task(listid, "task")
        result = self.taskmanager.move_task(taskid, 999)
        self.assertFalse(result)

    def test_add_color_tag(self):
        listid = self.taskmanager.add_list("list")
        taskid = self.tm.add_task(listid, "task")
        result = self.tm.add_color_tag(taskid, ColorTags.GREEN)
        self.assertTrue(result)
        self.assertEqual(self.tm.tasks[taskid].color_tag, ColorTags.GREEN)

    def test_add_color_tag_when_already_has_color(self):
        listid = self.taskmanager.add_list("list")
        taskid = self.taskmanager.add_task(listid, "task")
        self.taskmanager.add_color_tag(taskid, ColorTags.GREEN)
        result = self.taskmanager.add_color_tag(taskid, ColorTags.RED)
        self.assertFalse(result)

    def test_add_color_tag_non_existing_task(self):
        result = self.taskmanager.add_color_tag(999, ColorTags.GREEN)
        self.assertFalse(result)

    def test_remove_color_tag(self):
        listid = self.taskmanager.add_list("List")
        taskid = self.taskmanager.add_task(listid, "Task")
        self.taskmanager.add_color_tag(taskid, ColorTags.BLUE)
        self.taskmanager.remove_color_tag(taskid)
        self.assertEqual(self.tm.tasks[taskid].color_tag, ColorTags.NOTHING)

    def test_remove_color_tag_when_no_color(self):
        listid = self.taskmanager.add_list("List")
        taskid = self.taskmanager.add_task(listid, "Task")
        result = self.taskmanager.remove_color_tag(taskid)
        self.assertFalse(result)

    def test_remove_color_tag_non_existing_task(self):
        result = self.taskmanager.remove_color_tag(999)
        self.assertFalse(result)

    def test_change_color_tag(self):
        listid = self.taskmanager.add_list("List")
        taskid = self.taskmanager.add_task(listid, "Task")
        self.taskmanager.add_color_tag(taskid, ColorTags.GREEN)
        result = self.taskmanager.change_color_tag(taskid, ColorTags.RED)
        self.assertTrue(result)
        self.assertEqual(self.taskmanager.tasks[taskid].color_tag, ColorTags.RED)

    def test_change_color_tag_non_existing_task(self):
        result = self.taskmanager.change_color_tag(999, ColorTags.RED)
        self.assertFalse(result)

    #fetching tasks

    def test_get_list_tasks(self):
        listid = self.taskmanager.add_list("List")
        taskid = self.taskmanager.add_task(listid, "Task")
        result = self.taskmanager.get_list_tasks(listid)
        self.assertIn(taskid, result)

    def test_get_list_tasks_empty_list(self):
        listid = self.taskmanager.add_list("Empty list")
        result = self.taskmanager.get_list_tasks(listid)
        self.assertEqual(result, {})

    def test_get_list_tasks_non_existing_list(self):
        result = self.taskmanager.get_list_tasks(999)
        self.assertIsNone(result)

    def test_get_all_returns_dict(self):
        self.taskmanager.add_list("List A")
        self.taskmanager.add_list("List B")
        result = self.taskmanager.get_all()
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 2)


    #3. user manager tests

class TestUserManager(unittest.TestCase):

    def setUp(self):
        patcher_save = patch("app.models.save_to_json")
        patcher_push = patch("app.models.push_to_db")
        self.mock_save = patcher_save.start()
        self.mock_push = patcher_push.start()
        self.addCleanup(patcher_save.stop)
        self.addCleanup(patcher_push.stop)

        self.usermanager = UserManager()

    #registration

    def test_register_new_user(self):
        result = self.usermanager.register_user("janek", "haslo123")
        self.assertTrue(result)
        self.assertIn("janek", self.usermanager.users)

    def test_register_password_is_hashed(self):
        self.usermanager.register_user("janek", "haslo123")
        self.assertNotEqual(self.usermanager.users["janek"], "haslo123")

    def test_register_duplicate_username(self):
        self.usermanager.register_user("janek", "haslo123")
        result = self.usermanager.register_user("janek", "innehaslo")
        self.assertFalse(result)

    #Login

    def test_login_valid_credentials(self):
        self.usermanager.register_user("janek", "haslo123")
        result = self.usermanager.login_user("janek", "haslo123")
        self.assertTrue(result)

    def test_login_invalid_password(self):
        self.usermanager.register_user("janek", "haslo123")
        result = self.usermanager.login_user("janek", "zlehaslo")
        self.assertFalse(result)

    def test_login_non_existing_user(self):
        result = self.usermanager.login_user("widmo", "cokolwiek")
        self.assertFalse(result)

    #chenge password tests

    def test_change_password_valid(self):
        self.usermanager.register_user("janek", "old123")
        result = self.usermanager.change_password("janek", "old123", "new456")
        self.assertTrue(result)
        self.assertFalse(self.usermanager.login_user("janek", "old123"))
        self.assertTrue(self.usermanager.login_user("janek", "new456"))

    def test_change_password_wrong_old_password(self):
        self.usermanager.register_user("janek", "old123")
        result = self.usermanager.change_password("janek", "incorrectpassword", "new456")
        self.assertFalse(result)

    def test_change_password_non_existing_user(self):
        result = self.usermanager.change_password("widmo", "old", "new")
        self.assertFalse(result)

    #delete account

    def test_delete_account_valid(self):
        self.usermanager.register_user("janek", "password123")
        result = self.usermanager.delete_account("janek", "password123")
        self.assertTrue(result)
        self.assertNotIn("janek", self.usermanager.users)

    def test_delete_account_wrong_password(self):
        self.usermanager.register_user("janek", "password123")
        result = self.usermanager.delete_account("janek", "incorrectpassword")
        self.assertFalse(result)
        self.assertIn("janek", self.usermanager.users)

    def test_delete_account_non_existing_user(self):
        result = self.usermanager.delete_account("widmo", "whatever")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
