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

user_manager: UserManager

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

class TaskCreateRequest(BaseModel):
    name: str
    description: str = ""

class TaskUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color_tag: Optional[str] = None  # accepted as enum name string e.g. "GREEN"

class TaskMoveRequest(BaseModel):
    target_list_id: int
