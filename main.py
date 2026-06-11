"""
Todo backend — FastAPI + SQLAlchemy.

DB-agnostic: chay duoc voi sqlite:/// (test nhanh local) lan postgresql:// (tren cluster).
Doc cau hinh tu bien moi truong: DATABASE_URL, WELCOME_MESSAGE.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# --- Cau hinh tu bien moi truong (khong hardcode) ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./todo.db")
WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "Welcome to the Todo lab!")

# SQLite can connect_args dac thu; Postgres thi khong.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Todo(Base):
    """ORM model — mo ta bang 'todos'."""
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    done = Column(Boolean, default=False, nullable=False)


# --- Pydantic schema (validate du lieu vao/ra) ---
class TodoIn(BaseModel):
    title: str
    done: bool = False


class TodoOut(BaseModel):
    id: int
    title: str
    done: bool
    model_config = {"from_attributes": True}  # cho phep doc thang tu ORM object


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tu tao bang khi khoi dong (lab cho don gian; production dung migration).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Todo API", lifespan=lifespan)

# CORS mo de dev local (Vite 9991) goi duoc; tren cluster cung host nen vo hai.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/welcome")
def welcome():
    return {"message": WELCOME_MESSAGE}


@app.get("/api/todos", response_model=list[TodoOut])
def list_todos():
    with SessionLocal() as db:
        return db.query(Todo).order_by(Todo.id).all()


@app.post("/api/todos", response_model=TodoOut, status_code=201)
def create_todo(payload: TodoIn):
    with SessionLocal() as db:
        todo = Todo(title=payload.title, done=payload.done)
        db.add(todo)
        db.commit()
        db.refresh(todo)
        return todo


@app.put("/api/todos/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: int, payload: TodoIn):
    with SessionLocal() as db:
        todo = db.get(Todo, todo_id)
        if todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        todo.title = payload.title
        todo.done = payload.done
        db.commit()
        db.refresh(todo)
        return todo


@app.delete("/api/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    with SessionLocal() as db:
        todo = db.get(Todo, todo_id)
        if todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        db.delete(todo)
        db.commit()
