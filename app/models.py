from enum import Enum
from typing import Optional
from pydantic import BaseModel, model_validator, Field

from app.database import save_to_firestore, load_from_firestore_raw
from .hash import hash_password, verify_password

# ---------------------------------------------------------------------------
# TASK MODELS
# ---------------------------------------------------------------------------

class ColorTags(str, Enum):
    NOTHING = "NOTHING"
    GREEN = "GREEN"
    RED = "RED"
    YELLOW = "YELLOW"
    BLUE = "BLUE"
    PURPLE = "PURPLE"


class Task(BaseModel):
    name: str
    description: str = ""
    color_tag: ColorTags = ColorTags.NOTHING
    due_date: Optional[str] = None  # ISO date string "YYYY-MM-DD" or None


class TaskList(BaseModel):
    name: str
    task_ids: list[int] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# TASK MANAGER (BOARD-BASED)
# ---------------------------------------------------------------------------

class TaskManager(BaseModel):
    board_id: str = ""
    owner: str = ""
    name: str = ""
    users: list[str] = Field(default_factory=list)
    lists: dict[int, TaskList] = Field(default_factory=dict)
    tasks: dict[int, Task] = Field(default_factory=dict)
    list_order: list[int] = Field(default_factory=list)

    _next_list_id: int = 1
    _next_task_id: int = 1
    _batch: bool = False
    _dirty: bool = False

    model_config = {"arbitrary_types_allowed": True}

    # ---------------- INIT ----------------

    @model_validator(mode="after")
    def _init_counters(self):
        self._next_list_id = max(self.lists.keys(), default=0) + 1
        self._next_task_id = max(self.tasks.keys(), default=0) + 1

        existing = set(self.lists.keys())

        self.list_order = [lid for lid in self.list_order if lid in existing]

        for lid in self.lists:
            if lid not in self.list_order:
                self.list_order.append(lid)

        return self

    # ---------------- SAVE ----------------

    def _save(self):
        if self._batch:
            self._dirty = True
            return

        doc_id = f"board_{self.board_id}"
        save_to_firestore("boards", doc_id, self.model_dump(mode="json"))

    def begin_batch(self):
        self._batch = True
        self._dirty = False

    def end_batch(self):
        self._batch = False

        if self._dirty:
            self._dirty = False
            self._save()

    # ---------------- LISTS ----------------

    def add_list(self, name: str) -> int:
        list_id = self._next_list_id

        self.lists[list_id] = TaskList(name=name)
        self.list_order.append(list_id)

        self._next_list_id += 1
        self._save()

        return list_id

    def remove_list(self, list_id: int) -> bool:
        if list_id not in self.lists:
            return False

        # delete tasks inside list
        for task_id in self.lists[list_id].task_ids:
            self.tasks.pop(task_id, None)

        del self.lists[list_id]

        if list_id in self.list_order:
            self.list_order.remove(list_id)

        self._save()
        return True

    def rename_list(self, list_id: int, new_name: str) -> bool:
        if list_id not in self.lists:
            return False

        self.lists[list_id].name = new_name
        self._save()

        return True

    def reorder_lists(self, order: list[int]) -> bool:
        if set(order) != set(self.lists.keys()):
            return False

        self.list_order = order
        self._save()

        return True

    # ---------------- TASK HELPERS ----------------

    def _find_list_of_task(self, task_id: int) -> Optional[int]:
        return next(
            (lid for lid, lst in self.lists.items() if task_id in lst.task_ids),
            None
        )

    # ---------------- TASKS ----------------

    def add_task(
        self,
        list_id: int,
        name: str,
        description: str = "",
        due_date: Optional[str] = None,
    ) -> Optional[int]:
        if list_id not in self.lists:
            return None

        task_id = self._next_task_id

        self.tasks[task_id] = Task(
            name=name,
            description=description,
            due_date=due_date,
        )

        self.lists[list_id].task_ids.append(task_id)

        self._next_task_id += 1
        self._save()

        return task_id

    def remove_task(self, task_id: int) -> bool:
        if task_id not in self.tasks:
            return False

        list_id = self._find_list_of_task(task_id)

        if list_id is not None:
            if task_id in self.lists[list_id].task_ids:
                self.lists[list_id].task_ids.remove(task_id)

        self.tasks.pop(task_id, None)
        self._save()

        return True

    def move_task(self, task_id: int, target_list_id: int) -> bool:
        if task_id not in self.tasks or target_list_id not in self.lists:
            return False

        source_list_id = self._find_list_of_task(task_id)

        if source_list_id is None:
            return False

        if source_list_id == target_list_id:
            return True

        if task_id in self.lists[source_list_id].task_ids:
            self.lists[source_list_id].task_ids.remove(task_id)

        self.lists[target_list_id].task_ids.append(task_id)

        self._save()
        return True

    # ---------------- TASK UPDATES ----------------

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

    def change_color_tag(self, task_id: int, color_tag: ColorTags) -> bool:
        if task_id not in self.tasks:
            return False

        self.tasks[task_id].color_tag = color_tag
        self._save()

        return True

    def change_due_date(self, task_id: int, due_date: Optional[str]) -> bool:
        if task_id not in self.tasks:
            return False

        self.tasks[task_id].due_date = due_date
        self._save()

        return True

    # ---------------- READ ----------------

    def get_list_tasks(
        self,
        list_id: int,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        if list_id not in self.lists:
            return None

        all_ids = [tid for tid in self.lists[list_id].task_ids if tid in self.tasks]

        if page is None and limit is None:
            return {tid: self.tasks[tid] for tid in all_ids}

        page = max(1, int(page or 1))
        limit = max(1, int(limit or 10))

        total = len(all_ids)
        total_pages = max(1, (total + limit - 1) // limit) if total else 1
        page = min(page, total_pages)

        start = (page - 1) * limit
        end = start + limit
        page_ids = all_ids[start:end]

        return {
            "tasks": {tid: self.tasks[tid] for tid in page_ids},
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }

    def get_all(
        self,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> dict:
        paginated = page is not None or limit is not None

        result: dict = {}
        for list_id in self.list_order:
            if list_id not in self.lists:
                continue
            if paginated:
                paged = self.get_list_tasks(list_id, page=page, limit=limit)
                result[list_id] = {
                    "name": self.lists[list_id].name,
                    "tasks": paged["tasks"],
                    "page": paged["page"],
                    "limit": paged["limit"],
                    "total": paged["total"],
                    "total_pages": paged["total_pages"],
                }
            else:
                result[list_id] = {
                    "name": self.lists[list_id].name,
                    "tasks": self.get_list_tasks(list_id),
                }
        return result
    def get_board_name(self):
        return self.board_id


# ---------------------------------------------------------------------------
# USERS
# ---------------------------------------------------------------------------

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

    def _reload(self):
        data = load_from_firestore_raw("users", "users") or {}
        self.users = data.get("users", {})

    def _save(self):
        save_to_firestore("users", "users", {"users": self.users})

    def register_user(self, login, password) -> bool:
        self._reload()

        if login in self.users:
            return False

        self.users[login] = hash_password(password)
        self._save()

        return True

    def login_user(self, login, password) -> bool:
        self._reload()

        if login not in self.users:
            return False

        return verify_password(password, self.users[login])

    def change_password(self, login, old_password, new_password) -> bool:
        self._reload()

        if login not in self.users:
            return False

        if not verify_password(old_password, self.users[login]):
            return False

        self.users[login] = hash_password(new_password)
        self._save()

        return True

    def delete_account(self, login, password) -> bool:
        self._reload()

        if login not in self.users:
            return False

        if not verify_password(password, self.users[login]):
            return False

        del self.users[login]
        self._save()

        return True


# ---------------------------------------------------------------------------
# LOADER
# ---------------------------------------------------------------------------

def load_task_manager(board_id: str) -> TaskManager:
    data = load_from_firestore_raw("boards", f"board_{board_id}")

    if data is None:
        return TaskManager(board_id=board_id)

    data["board_id"] = board_id

    data["lists"] = {int(k): v for k, v in data.get("lists", {}).items()}
    data["tasks"] = {int(k): v for k, v in data.get("tasks", {}).items()}
    data["list_order"] = [int(x) for x in data.get("list_order", [])]

    # fix legacy color tags
    for task in data["tasks"].values():
        if isinstance(task.get("color_tag"), int):
            mapping = {
                1: "NOTHING",
                2: "GREEN",
                3: "RED",
                4: "YELLOW",
                5: "BLUE",
                6: "PURPLE"
            }
            task["color_tag"] = mapping.get(task["color_tag"], "NOTHING")

    for lst in data["lists"].values():
        lst["task_ids"] = [int(tid) for tid in lst.get("task_ids", [])]

    return TaskManager.model_validate(data)


Users = UserManager