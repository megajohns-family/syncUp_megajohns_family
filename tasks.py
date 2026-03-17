from pydantic import BaseModel, model_validator, Field


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

    def _find_list_of_task(self, task_id: int) -> int | None:
        return next((lid for lid, lst in self.lists.items() if task_id in lst.task_ids), None)

    def add_task(self, list_id: int, name: str, description: str = "") -> int | None:
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
            tasks = lst["tasks"]
            if not tasks:
                print("  (empty)")
            for task_id, task in tasks.items():
                print(f"  #{task_id}  {task.name}")
                if task.description:
                    print(f"       - {task.description}")
        print()
