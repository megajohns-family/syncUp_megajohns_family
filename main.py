from contextlib import asynccontextmanager
from app.models import TaskManager
from app.database import *
from fastapi import FastAPI

init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

manager = TaskManager()

todo = manager.add_list("To Do")
doing = manager.add_list("Doing")
done = manager.add_list("Done")

t1 = manager.add_task(todo, "Buy groceries", "Milk, bread, eggs")
t2 = manager.add_task(todo, "Do Python homework", "Chapter 4 exercises and quiz prep")
t3 = manager.add_task(doing, "Fix login bug", "Users getting 401 on valid credentials")
t4 = manager.add_task(todo, "Plan weekend trip", "Look into camping spots near the lake")
t5 = manager.add_task(done, "Set up repo", "Created GitHub org and invited family members")

manager.change_task_description(t3, "Users getting 401 on valid credentials — check JWT expiry logic")

manager.move_task(t2, doing)
manager.move_task(t3, done)
manager.save_to_json("app/json_files/tasks.json")
# manager.pull_from_db("tasks.json")
# manager = TaskManager.load_from_json("app/json_files/tasks.json")   
# manager.display()

