from taski import TaskManager

manager = TaskManager()


task1 = manager.add_task("Buy groceries")
task2 = manager.add_task("Do homework")

manager.add_description(task1, "Milk, bread, eggs")

manager.change_task_name(task2, "Do Python homework")


manager.change_description(task1, "Milk, bread, eggs, cheese")


manager.remove_description(task1)

manager.remove_task(task2)

print(manager.list_tasks())