from taski import TaskManager

manager = TaskManager()

todo   = manager.add_list("To Do")
doing  = manager.add_list("Doing")
done   = manager.add_list("Done")

t1 = manager.add_task(todo, "Buy groceries", "Milk, bread, eggs")
t2 = manager.add_task(todo, "Do Python homework")
t3 = manager.add_task(doing, "Fix login bug")

manager.move_task(t2, doing)  
manager.move_task(t3, done) 

def display(manager):
    for lst in manager.get_all().values():
        print(f"\n[ {lst['name']} ]")
        tasks = lst["tasks"]
        if not tasks:
            print("  (empty)")
        for task_id, task in tasks.items():
            desc = f" — {task['description']}" if task["description"] else ""
            print(f"  #{task_id} {task['name']}{desc}")

display(manager)
