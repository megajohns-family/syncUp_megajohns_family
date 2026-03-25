from app.models import TaskManager, load_from_firestore

manager = load_from_firestore(TaskManager)
manager.display()
