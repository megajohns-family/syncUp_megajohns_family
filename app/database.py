import json
import os

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

load_dotenv()

COLLECTION = "syncup"

_db = None


def _get_db():
    global _db
    if _db is None:
        raise RuntimeError("Firestore client not initialized. Call verify_firebase_connection() first.")
    return _db


def verify_firebase_connection() -> None:
    """
    Called once at startup. Validates all required env vars, initializes the
    Firebase Admin SDK using the Service Account JSON, and performs a test
    request to confirm connectivity. Raises RuntimeError on any failure —
    the server will not start.
    """
    global _db

    # 1. Check required env vars
    missing = []
    for var in ("FIREBASE_SERVICE_ACCOUNT", "SECRET_KEY"):
        if not os.getenv(var):
            missing.append(var)
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    # 2. Parse Service Account JSON
    raw = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    try:
        service_account_info = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"FIREBASE_SERVICE_ACCOUNT is not valid JSON: {e}"
        ) from e

    # 3. Initialize Firebase Admin SDK (only once)
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Firebase Admin SDK: {e}"
            ) from e

    # 4. Initialize Firestore client
    try:
        _db = firestore.client()
    except Exception as e:
        raise RuntimeError(f"Failed to create Firestore client: {e}") from e

    # 5. Test actual connectivity
    try:
        _db.collection(COLLECTION).document("_health_check").get()
    except Exception as e:
        raise RuntimeError(
            f"Firestore connectivity test failed: {e}"
        ) from e


# --- Public API ---

def save_to_firestore(doc_id: str, data: dict) -> None:
    _get_db().collection(COLLECTION).document(doc_id).set(data)


def invalidate_cache(doc_id: str) -> None:
    # Cache removed — firebase-admin handles connection pooling internally
    pass


def load_from_firestore_raw(doc_id: str) -> dict | None:
    doc = _get_db().collection(COLLECTION).document(doc_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()