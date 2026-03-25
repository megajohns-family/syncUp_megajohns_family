import os
import requests

COLLECTION = "syncup"

FIREBASE_PROJECT_ID = "syncup-3ad0e"
FIREBASE_API_KEY = "AIzaSyCg-2nIfs54Kv_XnLk_PMD-4H9F8RhF7tU"

_BASE = "https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/{collection}/{doc_id}"


def init_db() -> None:
    pass  

def _to_value(v) -> dict:
    if v is None:
        return {"nullValue": None}
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, str):
        return {"stringValue": v}
    if isinstance(v, list):
        return {"arrayValue": {"values": [_to_value(i) for i in v]}}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {k: _to_value(val) for k, val in v.items()}}}
    raise TypeError(f"Unsupported type for Firestore: {type(v)}")


def _from_value(v: dict):
    if "nullValue" in v:
        return None
    if "booleanValue" in v:
        return v["booleanValue"]
    if "integerValue" in v:
        return int(v["integerValue"])
    if "doubleValue" in v:
        return float(v["doubleValue"])
    if "stringValue" in v:
        return v["stringValue"]
    if "timestampValue" in v:
        return v["timestampValue"]
    if "arrayValue" in v:
        return [_from_value(i) for i in v["arrayValue"].get("values", [])]
    if "mapValue" in v:
        return {k: _from_value(val) for k, val in v["mapValue"].get("fields", {}).items()}
    raise ValueError(f"Unknown Firestore value type: {v}")


def _dict_to_fields(data: dict) -> dict:
    return {k: _to_value(v) for k, v in data.items()}


def _fields_to_dict(fields: dict) -> dict:
    return {k: _from_value(v) for k, v in fields.items()}


def _doc_url(doc_id: str) -> str:
    return _BASE.format(project=FIREBASE_PROJECT_ID, collection=COLLECTION, doc_id=doc_id)


# --- Public API ---

def save_to_firestore(doc_id: str, data: dict) -> None:
    url = _doc_url(doc_id)
    body = {"fields": _dict_to_fields(data)}
    resp = requests.patch(url, json=body, params={"key": FIREBASE_API_KEY})
    resp.raise_for_status()


def load_from_firestore_raw(doc_id: str) -> dict | None:
    url = _doc_url(doc_id)
    resp = requests.get(url, params={"key": FIREBASE_API_KEY})
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    return _fields_to_dict(data.get("fields", {}))
