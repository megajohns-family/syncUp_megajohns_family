from pydantic import BaseModel, model_validator, Field
from enum import Enum
from typing import Optional
import json
from .hash import hash_password, verify_password

class ColorTags(Enum):
    NOTHING = 1
    GREEN = 2
    RED = 3
    YELLOW = 4
    BLUE = 5
    PURPLE = 6

# Tasks and lists

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

    def add_list(self, name: str) -> int:
        list_id = self._next_list_id
        self.lists[list_id] = TaskList(name=name)
        self._next_list_id += 1
        return list_id

    def remove_list(self, list_id: int) -> bool:
        if list_id not in self.lists:
            return False
        for task_id in self.lists[list_id].task_ids:
            del self.tasks[task_id]
        del self.lists[list_id]
        return True

    def rename_list(self, list_id: int, new_name: str) -> bool:
        if list_id not in self.lists:
            return False
        self.lists[list_id].name = new_name
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
        return task_id

    def remove_task(self, task_id: int) -> bool:
        if task_id not in self.tasks:
            return False
        list_id = self._find_list_of_task(task_id)
        self.lists[list_id].task_ids.remove(task_id)
        del self.tasks[task_id]
        return True

    def change_task_name(self, task_id: int, new_name: str) -> bool:
        if task_id not in self.tasks:
            return False
        self.tasks[task_id].name = new_name
        return True

    def change_task_description(self, task_id: int, new_description: str) -> bool:
        if task_id not in self.tasks:
            return False
        self.tasks[task_id].description = new_description
        return True

    def move_task(self, task_id: int, target_list_id: int) -> bool:
        if task_id not in self.tasks or target_list_id not in self.lists:
            return False
        source_list_id = self._find_list_of_task(task_id)
        if source_list_id == target_list_id:
            return True
        self.lists[source_list_id].task_ids.remove(task_id)
        self.lists[target_list_id].task_ids.append(task_id)
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
        return True
    
    def remove_color_tag(self, task_id: int) -> bool:
        if task_id not in self.tasks:
            return False
        elif self.tasks[task_id].color_tag == ColorTags.NOTHING:
            return False
        
        self.tasks[task_id].color_tag = ColorTags.NOTHING

    def change_color_tag(self, task_id: int, color_tag: ColorTags) -> bool:
        if task_id not in self.tasks:
            return False
        self.tasks[task_id].color_tag = color_tag
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
            tasks = lst["tasks"]
            if not tasks:
                print("  (empty)")
            for task_id, task in tasks.items():
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
    filepath: str = "json/users.json"

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _load_users(self):
        try:
            with open(self.filepath) as f:
                self.users = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"File '{self.filepath}' does not exist. Make sure its present.")
        return self

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
        with open(self.filepath, "w") as f:
            json.dump(self.users, f, indent=2)
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
        with open(self.filepath, "w") as f:
            json.dump(self.users, f, indent=2)
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
        with open(self.filepath, "w") as f:
            json.dump(self.users, f, indent=2)
        print(f"Account {user_data.login} has been deleted successfully")
        return True


# For backward compatibility
Users = UserManager
