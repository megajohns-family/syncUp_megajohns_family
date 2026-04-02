from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.auth import create_access_token, get_current_user
from app.models import (
    ColorTags,
    UserManager,
    load_from_firestore,
    load_task_manager,
)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

user_manager: UserManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    global user_manager
    user_manager = load_from_firestore(UserManager)
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/static/html/landingpage.html")


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class UserCredentials(BaseModel):
    login: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ListCreateRequest(BaseModel):
    name: str

class ListRenameRequest(BaseModel):
    name: str

class ListOrderRequest(BaseModel):
    order: list[int]

class TaskCreateRequest(BaseModel):
    name: str
    description: str = ""

class TaskUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color_tag: Optional[ColorTags] = None

class TaskMoveRequest(BaseModel):
    target_list_id: int


# ---------------------------------------------------------------------------
# Auth routes (public)
# ---------------------------------------------------------------------------

@app.post("/users/register", status_code=201)
def register(body: UserCredentials):
    if not user_manager.register_user(body.login, body.password):
        raise HTTPException(status_code=400, detail="Login already taken or invalid input")
    return {"message": f"User '{body.login}' registered successfully"}


@app.post("/users/login")
def login(body: UserCredentials):
    if not user_manager.login_user(body.login, body.password):
        raise HTTPException(status_code=401, detail="Invalid login or password")
    token = create_access_token(body.login)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/users/change-password")
def change_password(body: ChangePasswordRequest, username: str = Depends(get_current_user)):
    if not user_manager.change_password(username, body.old_password, body.new_password):
        raise HTTPException(status_code=400, detail="Old password incorrect or user not found")
    return {"message": "Password changed successfully"}


@app.delete("/users/me")
def delete_account(body: UserCredentials, username: str = Depends(get_current_user)):
    if body.login != username:
        raise HTTPException(status_code=403, detail="Cannot delete another user's account")
    if not user_manager.delete_account(body.login, body.password):
        raise HTTPException(status_code=400, detail="Wrong password")
    return {"message": f"Account '{username}' deleted"}


# ---------------------------------------------------------------------------
# List routes (protected)
# ---------------------------------------------------------------------------

@app.get("/lists")
def get_lists(username: str = Depends(get_current_user)):
    manager = load_task_manager(username)
    return manager.get_all()


@app.post("/lists", status_code=201)
def create_list(body: ListCreateRequest, username: str = Depends(get_current_user)):
    manager = load_task_manager(username)
    list_id = manager.add_list(body.name)
    return {"list_id": list_id, "name": body.name}


@app.put("/lists/order")
def reorder_lists(body: ListOrderRequest, username: str = Depends(get_current_user)):
    manager = load_task_manager(username)
    if not manager.reorder_lists(body.order):
        raise HTTPException(status_code=400, detail="Order must contain exactly all existing list IDs")
    return {"message": "Order saved"}


@app.patch("/lists/{list_id}")
def rename_list(list_id: int, body: ListRenameRequest, username: str = Depends(get_current_user)):
    manager = load_task_manager(username)
    if not manager.rename_list(list_id, body.name):
        raise HTTPException(status_code=404, detail="List not found")
    return {"message": "List renamed"}


@app.delete("/lists/{list_id}")
def delete_list(list_id: int, username: str = Depends(get_current_user)):
    manager = load_task_manager(username)
    if not manager.remove_list(list_id):
        raise HTTPException(status_code=404, detail="List not found")
    return {"message": "List deleted"}


# ---------------------------------------------------------------------------
# Task routes (protected)
# ---------------------------------------------------------------------------

@app.post("/lists/{list_id}/tasks", status_code=201)
def create_task(list_id: int, body: TaskCreateRequest, username: str = Depends(get_current_user)):
    manager = load_task_manager(username)
    task_id = manager.add_task(list_id, body.name, body.description)
    if task_id is None:
        raise HTTPException(status_code=404, detail="List not found")
    return {"task_id": task_id, "name": body.name}


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdateRequest, username: str = Depends(get_current_user)):
    manager = load_task_manager(username)
    if task_id not in manager.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    manager.begin_batch()
    if body.name is not None:
        manager.change_task_name(task_id, body.name)
    if body.description is not None:
        manager.change_task_description(task_id, body.description)
    if body.color_tag is not None:
        manager.change_color_tag(task_id, body.color_tag)
    manager.end_batch()
    return {"message": "Task updated"}


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, username: str = Depends(get_current_user)):
    manager = load_task_manager(username)
    if not manager.remove_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted"}


@app.post("/tasks/{task_id}/move")
def move_task(task_id: int, body: TaskMoveRequest, username: str = Depends(get_current_user)):
    manager = load_task_manager(username)
    if not manager.move_task(task_id, body.target_list_id):
        raise HTTPException(status_code=404, detail="Task or target list not found")
    return {"message": "Task moved"}