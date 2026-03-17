class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.next_id = 1

    def add_task(self, name):
        task_id = self.next_id
        self.tasks[task_id] = {
            "name": name,
            "description": ""
        }
        self.next_id += 1
        return task_id

    def remove_task(self, task_id):
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False

    def change_task_name(self, task_id, new_name):
        if task_id in self.tasks:
            self.tasks[task_id]["name"] = new_name
            return True
        return False

    def add_description(self, task_id, description):
        if task_id in self.tasks:
            self.tasks[task_id]["description"] = description
            return True
        return False

    def change_description(self, task_id, new_description):
        if task_id in self.tasks:
            self.tasks[task_id]["description"] = new_description
            return True
        return False

    def remove_description(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id]["description"] = ""
            return True
        return False

    def list_tasks(self):
        return self.tasks