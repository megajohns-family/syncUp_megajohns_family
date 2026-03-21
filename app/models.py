import json
from app.database import get_db
from pydantic import BaseModel, model_validator, Field
from pathlib import Path

#Files which program operates on:

users = Path("app/json_files/users.json")
tasks = Path("app/json_files/tasks.json")

class Task(BaseModel):
    name: str
    description: str = ""


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
        self.save_to_json(tasks)
        self.push_to_db("tasks.json")
        return list_id
        

    def remove_list(self, list_id: int) -> bool:
        if list_id not in self.lists:
            return False
        for task_id in self.lists[list_id].task_ids:
            del self.tasks[task_id]
        del self.lists[list_id]
        self.save_to_json(tasks)
        self.push_to_db("tasks.json")
        return True

    def rename_list(self, list_id: int, new_name: str) -> bool:
        if list_id not in self.lists:
            return False
        self.lists[list_id].name = new_name
        self.save_to_json(tasks)
        self.push_to_db("tasks.json")
        return True

    def _find_list_of_task(self, task_id: int) -> int | None:
        return next((lid for lid, lst in self.lists.items() if task_id in lst.task_ids), None)

    def add_task(self, list_id: int, name: str, description: str = "") -> int | None:
        if list_id not in self.lists:
            return None
        task_id = self._next_task_id
        self.tasks[task_id] = Task(name=name, description=description)
        self.lists[list_id].task_ids.append(task_id)
        self._next_task_id += 1
        self.save_to_json(tasks)
        self.push_to_db("tasks.json")
        return task_id

    def remove_task(self, task_id: int) -> bool:
        if task_id not in self.tasks:
            return False
        list_id = self._find_list_of_task(task_id)
        self.lists[list_id].task_ids.remove(task_id)
        del self.tasks[task_id]
        self.save_to_json(tasks)
        self.push_to_db("tasks.json")
        return True

    def change_task_name(self, task_id: int, new_name: str) -> bool:
        if task_id not in self.tasks:
            return False
        self.tasks[task_id].name = new_name
        self.save_to_json(tasks)
        self.push_to_db("tasks.json")
        return True

    def change_task_description(self, task_id: int, new_description: str) -> bool:
        if task_id not in self.tasks:
            return False
        self.tasks[task_id].description = new_description
        self.save_to_json(tasks)
        self.push_to_db("tasks.json")
        return True

    def move_task(self, task_id: int, target_list_id: int) -> bool:
        if task_id not in self.tasks or target_list_id not in self.lists:
            return False
        source_list_id = self._find_list_of_task(task_id)
        if source_list_id == target_list_id:
            return True
        self.lists[source_list_id].task_ids.remove(task_id)
        self.lists[target_list_id].task_ids.append(task_id)
        self.save_to_json(tasks)
        self.push_to_db("tasks.json")
        return True

    def get_list_tasks(self, list_id: int) -> dict[int, Task] | None:
        if list_id not in self.lists:
            return None
        return {tid: self.tasks[tid] for tid in self.lists[list_id].task_ids}

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
                print(f"  #{task_id}  {task.name}")
                if task.description:
                    print(f"       - {task.description}")
                    print()

    def save_to_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_json(cls, path: str) -> "TaskManager":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["lists"] = {int(k): v for k, v in data.get("lists", {}).items()}
        data["tasks"] = {int(k): v for k, v in data.get("tasks", {}).items()}
        for lst in data["lists"].values():
            lst["task_ids"] = [int(tid) for tid in lst.get("task_ids", [])]
        return cls.model_validate(data)

    def push_to_db(self, filename: str) -> None:
        if filename == "tasks.json":
            path = tasks
        elif filename == "users.json":
            path = users
        else:
            print("File not found")
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        with get_db() as db:
            if filename == "tasks.json":
                db.execute(
                    "INSERT OR REPLACE INTO tasks(file_name, file_data) VALUES (?, ?)",
                    (filename, json.dumps(data, ensure_ascii=False))
                )
                db.commit()
            elif filename == "users.json":
                db.execute(
                    "INSERT OR REPLACE INTO users(file_name, file_data) VALUES (?, ?)",
                    (filename, json.dumps(data, ensure_ascii=False))
                )
                db.commit()

    def pull_from_db(self, filename: str) -> None:
        with get_db() as db:
            if filename == "tasks.json":
                row = db.execute(
                    "SELECT file_data FROM tasks WHERE file_name = ?",
                    (filename,)
                ).fetchone()

                if row is None:
                    print(f"There is no data for {filename} in database")
                    return

                data = json.loads(row["file_data"])

                with open(tasks, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            elif filename == "users.json":
                row = db.execute(
                    "SELECT users_file_data FROM users WHERE users_file_name = ?",
                    (filename,)
                ).fetchone()

                if row is None:
                    print(f"There is no data for {filename} in database")
                    return

                data = json.loads(row["users_file_data"])

                with open(users, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            else:
                print(f"Nieznany plik: {filename}")

    # class ValidUsers(BaseModel):
    #     #Add validanion here
    #     pass
                