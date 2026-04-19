from contextlib import asynccontextmanager
from typing import List
from collections import defaultdict
import asyncio

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.database import verify_firebase_connection
from app.auth import create_access_token, get_current_user
from app.models import (
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

    async def connect(self, websocket: WebSocket, board_id: str):
        await websocket.accept()
        self.rooms[board_id].append(websocket)

    def disconnect(self, websocket: WebSocket, board_id: str):
        if websocket in self.rooms[board_id]:
            self.rooms[board_id].remove(websocket)

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

@app.websocket("/ws/{board_id}")
async def websocket_endpoint(websocket: WebSocket, board_id: str):
    await manager_ws.connect(websocket, board_id)

    try:
        while True:
            await websocket.receive_text()
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

@app.post("/users/register", status_code=201)
def register(body: UserCredentials):
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

    return {"ok": True}