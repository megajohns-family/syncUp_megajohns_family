from database import verify_firebase_connection, _get_db

verify_firebase_connection()
db = _get_db()

SOURCE_COLLECTION = "syncup"
TARGET_COLLECTION = "boards"


def migrate():
    print("🚀 Starting migration v2...")

    docs = db.collection(SOURCE_COLLECTION).stream()

    for doc in docs:
        username = doc.id
        data = doc.to_dict() or {}

        board_id = f"board_{username}"
        board_ref = db.collection(TARGET_COLLECTION).document(board_id)

        print(f"➡ Migrating {username} -> {board_id}")

        # ---------------------------
        # NORMALIZE DATA
        # ---------------------------

        lists = data.get("lists", {})
        tasks = data.get("tasks", {})
        list_order = data.get("list_order", [])

        if isinstance(lists, list):
            lists = {str(i): v for i, v in enumerate(lists)}

        if isinstance(tasks, list):
            tasks = {str(i): v for i, v in enumerate(tasks)}

        list_order = [int(x) for x in list_order] if list_order else []

        # ---------------------------
        # WRITE BOARD (OVERWRITE SAFE)
        # ---------------------------

        board_data = {
            "owner": username,
            "users": [username],

            "lists": lists,
            "tasks": tasks,
            "list_order": list_order,
        }

        board_ref.set(board_data)

    print("✅ Migration v2 completed successfully")


if __name__ == "__main__":
    migrate()