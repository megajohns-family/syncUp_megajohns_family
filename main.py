from contextlib import asynccontextmanager
from typing import List
from collections import defaultdict
import asyncio
import time

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.database import verify_firebase_connection, save_to_firestore, get_user_boards
from app.auth import create_access_token, get_current_user, decode_token
from app.models import (
    TaskManager,
    UserManager,
    load_task_manager
)

# ---------------------------------------------------------------------------
# APP LIFECYCLE
# ---------------------------------------------------------------------------

user_manager: UserManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global user_manager
    verify_firebase_connection()
    user_manager = UserManager()
    yield

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------------------------------------------------------------------
# ROOT
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return RedirectResponse(url="/static/html/landingpage.html")

# ---------------------------------------------------------------------------
# WEBSOCKET (BOARD ROOMS)
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, List[WebSocket]] = defaultdict(list)
        self.users: dict[WebSocket, str] = {}  # ws -> username

    async def connect(self, websocket: WebSocket, board_id: str, username: str):
        await websocket.accept()
        self.rooms[board_id].append(websocket)
        self.users[websocket] = username

    def disconnect(self, websocket: WebSocket, board_id: str):
        if websocket in self.rooms[board_id]:
            self.rooms[board_id].remove(websocket)
        self.users.pop(websocket, None)

    def get_active_users(self, board_id: str) -> list[str]:
        return [self.users[ws] for ws in self.rooms.get(board_id, []) if ws in self.users]

    async def broadcast(self, board_id: str, message: dict):
        if board_id not in self.rooms:
            return

        dead = []

        for ws in self.rooms[board_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.rooms[board_id].remove(ws)

manager_ws = ConnectionManager()

# @app.websocket("/ws/{board_id}")
# async def websocket_endpoint(websocket: WebSocket, board_id: str, token: str):
#     username = decode_token(token)
#     if not username:
#         await websocket.close()
#         return
#     await manager_ws.connect(websocket, board_id, username)
#     try:
#         while True:
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         manager_ws.disconnect(websocket, board_id)
@app.websocket("/ws/{board_id}")
async def websocket_endpoint(websocket: WebSocket, board_id: str, token: str):
    username = decode_token(token)
    if not username:
        await websocket.close()
        return
    await manager_ws.connect(websocket, board_id, username)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager_ws.disconnect(websocket, board_id)

# ---------------------------------------------------------------------------
# SCHEMAS
# ---------------------------------------------------------------------------

class ListCreateRequest(BaseModel):
    name: str

class ListRenameRequest(BaseModel):
    name: str

class TaskCreateRequest(BaseModel):
    name: str
    description: str = ""

class TaskMoveRequest(BaseModel):
    target_list_id: int

class UserCredentials(BaseModel):
    login: str
    password: str

# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

REGISTER_COOLDOWN_SECONDS = 5
_last_register_attempt: dict[str, float] = {}

@app.post("/users/register", status_code=201)
def register(body: UserCredentials, request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    last = _last_register_attempt.get(ip)
    if last is not None and now - last < REGISTER_COOLDOWN_SECONDS:
        retry_after = int(REGISTER_COOLDOWN_SECONDS - (now - last)) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Too many registration attempts. Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )
    _last_register_attempt[ip] = now

    if not user_manager.register_user(body.login, body.password):
        raise HTTPException(status_code=400, detail="User exists or invalid data")
    return {"message": "registered"}

@app.post("/users/login")
def login(body: UserCredentials):
    if not user_manager.login_user(body.login, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "access_token": create_access_token(body.login),
        "token_type": "bearer"
    }
# ---------------------------------------------------------------------------
# BOARD HELPERS
# ---------------------------------------------------------------------------

def get_board(board_id: str):
    manager = load_task_manager(board_id)
    if not manager:
        raise HTTPException(status_code=404, detail="Board not found")
    return manager

class BoardCreateRequest(BaseModel):
    name: str

@app.get("/boards")
def list_boards(username: str = Depends(get_current_user)):
    return get_user_boards(username)

@app.post("/boards", status_code=201)
def create_board(body: BoardCreateRequest, username: str = Depends(get_current_user)):
    import uuid
    board_id = str(uuid.uuid4())[:8]
    manager = TaskManager(board_id=board_id, name=body.name, owner=username, users=[])
    save_to_firestore("boards", f"board_{board_id}", manager.model_dump(mode="json"))
    return {"board_id": board_id}

class BoardAddUserRequest(BaseModel):
    username: str

@app.post("/boards/{board_id}/users")
async def add_user_to_board(board_id: str, body: BoardAddUserRequest, username: str = Depends(get_current_user)):
    manager = get_board(board_id)
    if username != manager.owner:
        raise HTTPException(status_code=403, detail="Only owner can add users")
    if body.username not in manager.users:
        manager.users.append(body.username)
        manager._save()
        await manager_ws.broadcast(board_id, {
        "event": "user_added",
        "data": {"username": username}
        })
    return {"ok": True}

@app.get("/boards/{board_id}/users")
def get_board_users(board_id: str, username: str = Depends(get_current_user)):
    manager = get_board(board_id)
    return {"owner": manager.owner, "users": manager.users}

@app.delete("/boards/{board_id}/users/{target_username}")
async def remove_user_from_board(board_id: str, target_username: str, username: str = Depends(get_current_user)):
    manager = get_board(board_id)
    print(f"requesting user: {username}, owner: {manager.owner}")
    if username != manager.owner:
        raise HTTPException(status_code=403, detail="Only owner can remove users")
    if target_username in manager.users:
        manager.users.remove(target_username)
        manager._save()
    await manager_ws.broadcast(board_id, {
        "event": "user_removed",
        "data": {"username": target_username}
    })
    return {"ok": True}

# ---------------------------------------------------------------------------
# LISTS
# ---------------------------------------------------------------------------

@app.post("/boards/{board_id}/lists", status_code=201)
async def create_list(
    board_id: str,
    body: ListCreateRequest,
    username: str = Depends(get_current_user)
):
    manager = get_board(board_id)

    list_id = manager.add_list(body.name)

    await manager_ws.broadcast(board_id, {
        "event": "list_created",
        "data": {"list_id": list_id, "name": body.name}
    })

    return {"list_id": list_id}

@app.get("/boards/{board_id}/lists")
def get_lists(board_id: str, username: str = Depends(get_current_user)):
    manager = get_board(board_id)
    return manager.get_all()

@app.patch("/boards/{board_id}/lists/{list_id}")
async def rename_list(board_id: str, list_id: int, body: ListRenameRequest):
    manager = get_board(board_id)

    if not manager.rename_list(list_id, body.name):
        raise HTTPException(status_code=404)

    await manager_ws.broadcast(board_id, {
        "event": "list_renamed",
        "data": {"list_id": list_id, "name": body.name}
    })

    return {"ok": True}

@app.delete("/boards/{board_id}/lists/{list_id}")
async def delete_list(board_id: str, list_id: int):
    manager = get_board(board_id)

    manager.remove_list(list_id)

    await manager_ws.broadcast(board_id, {
        "event": "list_deleted",
        "data": {"list_id": list_id}
    })

    return {"ok": True}

# ---------------------------------------------------------------------------
# TASKS
# ---------------------------------------------------------------------------

@app.post("/boards/{board_id}/lists/{list_id}/tasks", status_code=201)
async def create_task(board_id: str, list_id: int, body: TaskCreateRequest):
    manager = get_board(board_id)

    task_id = manager.add_task(list_id, body.name, body.description)

    await manager_ws.broadcast(board_id, {
        "event": "task_created",
        "data": {
            "task_id": task_id,
            "list_id": list_id,
            "name": body.name
        }
    })

    return {"task_id": task_id}

@app.post("/boards/{board_id}/tasks/{task_id}/move")
async def move_task(board_id: str, task_id: int, body: TaskMoveRequest):
    manager = get_board(board_id)

    manager.move_task(task_id, body.target_list_id)

    await manager_ws.broadcast(board_id, {
        "event": "task_moved",
        "data": {
            "task_id": task_id,
            "target_list_id": body.target_list_id
        }
    })

    return {"ok": True}

@app.patch("/boards/{board_id}/tasks/{task_id}")
def update_task(board_id: str, task_id: int, body: dict):
    manager = load_task_manager(board_id)

    if "name" in body:
        manager.change_task_name(task_id, body["name"])

    if "description" in body:
        manager.change_task_description(task_id, body["description"])

    if "color_tag" in body:
        manager.change_color_tag(task_id, body["color_tag"])

    if "due_date" in body:
        manager.change_due_date(task_id, body["due_date"] or None)

    return {"ok": True}

@app.delete("/boards/{board_id}/tasks/{task_id}")
async def delete_task(board_id: str, task_id: int):
    manager = get_board(board_id)
    manager.remove_task(task_id)
    await manager_ws.broadcast(board_id, {
        "event": "task_deleted",
        "data": {"task_id": task_id}
    })
    return {"ok": True}

@app.put("/boards/{board_id}/lists/order")
async def reorder_lists(board_id: str, body: dict):
    manager = get_board(board_id)
    if not manager.reorder_lists(body["order"]):
        raise HTTPException(status_code=400, detail="Invalid order")
    await manager_ws.broadcast(board_id, {
        "event": "lists_reordered",
        "data": {"order": body["order"]}
    })
    return {"ok": True}

@app.get("/board_name")
def load_board():
    return {"board_name" : get_board("tasks_test")}

@app.get("/boards/{board_id}/search")
def search_tasks(board_id: str, q: str, username: str = Depends(get_current_user)):
    manager = get_board(board_id)
    q = q.lower()
    results = []
    for task_id, task in manager.tasks.items():
        if q in task.name.lower() or q in task.description.lower():
            list_id = manager._find_list_of_task(task_id)
            results.append({
                "task_id": task_id,
                "name": task.name,
                "description": task.description,
                "color_tag": task.color_tag,
                "list_id": list_id,
                "list_name": manager.lists[list_id].name if list_id else ""
            })
    return results

#3 accounts
#Showcase - owner
#Showcase2, Showcase3 - users
#Same pw: Showcase