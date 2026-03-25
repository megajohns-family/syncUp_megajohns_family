from enum import Enum
from typing import Optional
from pydantic import BaseModel, model_validator, Field
from app.database import save_to_firestore, load_from_firestore_raw
from .hash import hash_password, verify_password


class ColorTags(Enum):
    NOTHING = 1
    GREEN = 2
    RED = 3
    YELLOW = 4
    BLUE = 5
    PURPLE = 6

class Task(BaseModel):
    name: str
    description: str = ""
    color_tag: ColorTags = ColorTags.NOTHING

class TaskList(BaseModel):
    name: str
    task_ids: list[int] = Field(default_factory=list)

class TaskManager(BaseModel):
    lists: dict[int, TaskList] = Field(default_factory=dict)
    tasks: dict[int, Task] = Field(default_factory=dict)
    _next_list_id: int = 1
    _next_task_id: int = 1

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _init_counters(self):
        self._next_list_id = max(self.lists.keys(), default=0) + 1
        self._next_task_id = max(self.tasks.keys(), default=0) + 1
        return self

    def _save(self):
        save_to_firestore("tasks", self.model_dump(mode="json"))

    def add_list(self, name: str) -> int:
        list_id = self._next_list_id
        self.lists[list_id] = TaskList(name=name)
        self._next_list_id += 1
        self._save()
        return list_id

    def remove_list(self, list_id: int) -> bool:
        if list_id not in self.lists:
            return False
        for task_id in self.lists[list_id].task_ids:
            del self.tasks[task_id]
        del self.lists[list_id]
        self._save()
        return True

    def rename_list(self, list_id: int, new_name: str) -> bool:
        if list_id not in self.lists:
            return False
        self.lists[list_id].name = new_name
        self._save()
        return True

    def _find_list_of_task(self, task_id: int) -> Optional[int]:
        return next((lid for lid, lst in self.lists.items() if task_id in lst.task_ids), None)

    def add_task(self, list_id: int, name: str, description: str = "") -> Optional[int]:
        if list_id not in self.lists:
            return None
        task_id = self._next_task_id
        self.tasks[task_id] = Task(name=name, description=description)
        self.lists[list_id].task_ids.append(task_id)
        self._next_task_id += 1
        self._save()
        return task_id

    def remove_task(self, task_id: int) -> bool:
        if task_id not in self.tasks:
            return False
        list_id = self._find_list_of_task(task_id)
        self.lists[list_id].task_ids.remove(task_id)
        del self.tasks[task_id]
        self._save()
        return True

    def change_task_name(self, task_id: int, new_name: str) -> bool:
        if task_id not in self.tasks:
            return False
        self.tasks[task_id].name = new_name
        self._save()
        return True

    def change_task_description(self, task_id: int, new_description: str) -> bool:
        if task_id not in self.tasks:
            return False
        self.tasks[task_id].description = new_description
        self._save()
        return True

    def move_task(self, task_id: int, target_list_id: int) -> bool:
        if task_id not in self.tasks or target_list_id not in self.lists:
            return False
        source_list_id = self._find_list_of_task(task_id)
        if source_list_id == target_list_id:
            return True
        self.lists[source_list_id].task_ids.remove(task_id)
        self.lists[target_list_id].task_ids.append(task_id)
        self._save()
        return True

    def get_list_tasks(self, list_id: int) -> Optional[dict[int, Task]]:
        if list_id not in self.lists:
            return None
        return {tid: self.tasks[tid] for tid in self.lists[list_id].task_ids}

    def add_color_tag(self, task_id: int, color_tag: ColorTags) -> bool:
        if task_id not in self.tasks:
            return False
        elif self.tasks[task_id].color_tag != ColorTags.NOTHING:
            return False
        self.tasks[task_id].color_tag = color_tag
        self._save()
        return True

    def remove_color_tag(self, task_id: int) -> bool:
        if task_id not in self.tasks:
            return False
        elif self.tasks[task_id].color_tag == ColorTags.NOTHING:
            return False
        self.tasks[task_id].color_tag = ColorTags.NOTHING
        self._save()

    def change_color_tag(self, task_id: int, color_tag: ColorTags) -> bool:
        if task_id not in self.tasks:
            return False
        self.tasks[task_id].color_tag = color_tag
        self._save()
        return True

    def get_all(self) -> dict:
        return {
            list_id: {
                "name": lst.name,
                "tasks": self.get_list_tasks(list_id),
            }
            for list_id, lst in self.lists.items()
        }

    def display(self) -> None:
        for lst in self.get_all().values():
            print(f"\n[ {lst['name']} ]")
            tsks = lst["tasks"]
            if not tsks:
                print("  (empty)")
            for task_id, task in tsks.items():
                color = f" [{task.color_tag.name}]" if task.color_tag != ColorTags.NOTHING else ""
                print(f"  #{task_id}  {task.name}{color}")
                if task.description:
                    print(f"       - {task.description}")
                    print()


# Users

class User(BaseModel):
    login: str
    password: str

class UserLogin(BaseModel):
    login: str
    password: str

class UserPasswordChange(BaseModel):
    login: str
    old_password: str
    new_password: str

class UserDelete(BaseModel):
    login: str
    password: str

class UserManager(BaseModel):
    users: dict[str, str] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    def _save(self):
        save_to_firestore("users", self.model_dump(mode="json"))

    def register_user(self, login, password) -> bool:
        try:
            user_data = User(login=login, password=password)
        except ValueError as e:
            print(f"Invalid input: {e}")
            return False

        if user_data.login in self.users:
            print("Login is already taken, choose a different one")
            return False
        self.users[user_data.login] = hash_password(user_data.password)
        self._save()
        print(f"Successfully registered, welcome {user_data.login}!")
        return True

    def login_user(self, login, password) -> bool:
        try:
            user_data = UserLogin(login=login, password=password)
        except ValueError as e:
            print(f"Invalid input: {e}")
            return False

        if user_data.login not in self.users:
            print(f"{user_data.login} is not registered yet")
            return False

        if not verify_password(user_data.password, self.users[user_data.login]):
            print("Wrong password")
            return False

        print(f"Successfully logged in, welcome back {user_data.login}!")
        return True

    def change_password(self, login, old_password, new_password) -> bool:
        try:
            user_data = UserPasswordChange(login=login, old_password=old_password, new_password=new_password)
        except ValueError as e:
            print(f"Invalid input: {e}")
            return False

        if user_data.login not in self.users:
            print(f"{user_data.login} is not registered yet")
            return False

        if not verify_password(user_data.old_password, self.users[user_data.login]):
            print("Old password does not match")
            return False

        self.users[user_data.login] = hash_password(user_data.new_password)
        self._save()
        print("Password changed successfully!")
        return True

    def delete_account(self, login, password) -> bool:
        try:
            user_data = UserDelete(login=login, password=password)
        except ValueError as e:
            print(f"Invalid input: {e}")
            return False

        if user_data.login not in self.users:
            print(f"{user_data.login} is not registered yet")
            return False

        if not verify_password(user_data.password, self.users[user_data.login]):
            print("Wrong password")
            return False

        del self.users[user_data.login]
        self._save()
        print(f"Account {user_data.login} has been deleted successfully")
        return True


def load_from_firestore(cls: "type[TaskManager] | type[UserManager]") -> "TaskManager | UserManager":
    doc_id = "tasks" if cls is TaskManager else "users"
    data = load_from_firestore_raw(doc_id)
    if data is None:
        return cls()
    if cls is TaskManager:
        data["lists"] = {int(k): v for k, v in data.get("lists", {}).items()}
        data["tasks"] = {int(k): v for k, v in data.get("tasks", {}).items()}
        for lst in data["lists"].values():
            lst["task_ids"] = [int(tid) for tid in lst.get("task_ids", [])]
    return cls.model_validate(data)


# For backward compatibility
Users = UserManager
