from contextlib import asynccontextmanager
from app.models import TaskManager, ColorTags, UserManager, load_from_json, save_to_json
from app.database import *
from fastapi import FastAPI

init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# User management
print("=== USER MANAGEMENT ===\n")
users = load_from_json(UserManager, users)

# Register users
# print("Registering users...")
# users.register_user("john", "password123")
# users.register_user("jane", "securepass456")

# Login attempts
print("\nLogging in...")
users.login_user("john", "password123")
users.login_user("jane", "wrongpassword")  # This will fail

# Change password
# print("\nChanging password...")
# users.change_password("john", "password123", "newpassword789")

print("\n" + "="*40 + "\n")

# Task management
print("=== TASK MANAGEMENT ===\n")
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
# manager.pull_from_db("tasks.json")
# manager = TaskManager.load_from_json("app/json_files/tasks.json")   
# manager.display()

manager.add_color_tag(t1, ColorTags.GREEN)
manager.change_color_tag(t1, ColorTags.PURPLE)

manager.add_color_tag(t3, ColorTags.GREEN)
manager.remove_color_tag(t3)

manager.add_color_tag(t5, ColorTags.RED)
manager.change_color_tag(t5, ColorTags.YELLOW)

manager.display()
