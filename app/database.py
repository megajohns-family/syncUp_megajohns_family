import json
import os

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

load_dotenv()

# ---------------------------------------------------------------------------
# FIREBASE INIT
# ---------------------------------------------------------------------------

_db = None


def _get_db():
    global _db
    if _db is None:
        raise RuntimeError(
            "Firestore client not initialized. Call verify_firebase_connection() first."
        )
    return _db


def verify_firebase_connection() -> None:
    """
    Initializes Firebase Admin SDK and Firestore client.
    Must be called once at app startup.
    """
    global _db

    # ---------------- ENV CHECK ----------------
    missing = []
    for var in ("FIREBASE_SERVICE_ACCOUNT", "SECRET_KEY"):
        if not os.getenv(var):
            missing.append(var)

    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    # ---------------- PARSE SERVICE ACCOUNT ----------------
    raw = os.getenv("FIREBASE_SERVICE_ACCOUNT")

    try:
        service_account_info = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"FIREBASE_SERVICE_ACCOUNT is not valid JSON: {e}"
        ) from e

    # ---------------- INIT FIREBASE ----------------
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Firebase Admin SDK: {e}"
            ) from e

    # ---------------- INIT FIRESTORE ----------------
    try:
        _db = firestore.client()
    except Exception as e:
        raise RuntimeError(
            f"Failed to create Firestore client: {e}"
        ) from e

    # ---------------- HEALTH CHECK ----------------
    try:
        _db.collection("health").document("_check").get()
    except Exception as e:
        raise RuntimeError(
            f"Firestore connectivity test failed: {e}"
        ) from e


# ---------------------------------------------------------------------------
# GENERIC FIRESTORE API (CLEAN ARCHITECTURE)
# ---------------------------------------------------------------------------

def save_to_firestore(collection: str, doc_id: str, data: dict) -> None:
    """
    Save document to specific collection.
    Example:
        save_to_firestore("boards", "board_abc", {...})
    """
    _get_db().collection(collection).document(doc_id).set(data)


def load_from_firestore_raw(collection: str, doc_id: str) -> dict | None:
    """
    Load document from specific collection.
    """
    doc = _get_db().collection(collection).document(doc_id).get()

    if not doc.exists:
        return None

    return doc.to_dict()


def delete_from_firestore(collection: str, doc_id: str) -> None:
    """
    Optional helper for future use.
    """
    _get_db().collection(collection).document(doc_id).delete()

def get_user_boards(username: str) -> list[dict]:
    db = _get_db()
    boards = []
    owned = db.collection("boards").where("owner", "==", username).stream()
    for doc in owned:
        d = doc.to_dict()
        bid = doc.id.replace("board_", "")
        boards.append({"id": bid, "name": d.get("name", bid), "owner": d.get("owner", "")})
    shared = db.collection("boards").where("users", "array_contains", username).stream()
    for doc in shared:
        d = doc.to_dict()
        bid = doc.id.replace("board_", "")
        if not any(b["id"] == bid for b in boards):
            boards.append({"id": bid, "name": d.get("name", bid), "owner": d.get("owner", "")})
    return boards