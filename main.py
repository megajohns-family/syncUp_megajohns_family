from app.models import TaskManager, load_from_firestore
from app.database import init_db

init_db()

print("=== TASK MANAGEMENT ===\n")
manager = load_from_firestore(TaskManager)
manager.display()
