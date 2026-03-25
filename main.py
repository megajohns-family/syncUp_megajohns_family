from contextlib import asynccontextmanager
from app.models import TaskManager, ColorTags, UserManager, load_from_firestore
from app.database import init_db
from fastapi import FastAPI

init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# User management
print("=== USER MANAGEMENT ===\n")
users = load_from_firestore(UserManager)

# Register users
# print("Registering users...")
# users.register_user("john", "password123")
# users.register_user("jane", "securepass456")

# Login attempts
# print("\nLogging in...")
# users.login_user("john", "password123")
# users.login_user("jane", "wrongpassword")  # This will fail

# Change password
# print("\nChanging password...")
# users.change_password("john", "password123", "newpassword789")

print("\n" + "="*40 + "\n")

# Task management
print("=== TASK MANAGEMENT ===\n")
manager = load_from_firestore(TaskManager)

manager.display()
