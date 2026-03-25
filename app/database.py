import firebase_admin
from firebase_admin import credentials, firestore as fb_firestore
from dotenv import load_dotenv
import os

COLLECTION = "syncup"

load_dotenv()
SERVICE_ACCOUNT_KEY = os.getenv("FIREBASE_CREDENTIALS_PATH")


def init_db():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
        firebase_admin.initialize_app(cred)


def get_db():
    return fb_firestore.client()


def save_to_firestore(doc_id: str, data: dict) -> None:
    get_db().collection(COLLECTION).document(doc_id).set(data)


def load_from_firestore_raw(doc_id: str) -> dict | None:
    doc = get_db().collection(COLLECTION).document(doc_id).get()
    return doc.to_dict() if doc.exists else None
