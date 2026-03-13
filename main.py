from fastapi import FastAPI
from app.database import *

app = FastAPI()

@app.on_event("startup")
def start():
    init_db()