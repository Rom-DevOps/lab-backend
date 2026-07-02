"""
Ứng dụng Backend cho danh sách công việc (Todo) — viết bằng FastAPI và SQLAlchemy.

Thiết kế độc lập cơ sở dữ liệu (Database-agnostic): Ứng dụng tự động tương thích và chạy được với cả SQLite
(kết nối nhanh dưới local) lẫn PostgreSQL (khi triển khai thực tế trên Kubernetes Cluster).
Cấu hình ứng dụng được đọc động từ biến môi trường: DATABASE_URL, WELCOME_MESSAGE.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# --- Cấu hình ứng dụng từ biến môi trường (tránh hardcode thông tin đặc thù) ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./todo.db")
WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "Welcome to the Todo lab!")
APP_VERSION = os.getenv("APP_VERSION", "1.1.0")  # Tăng số phiên bản khi cần tạo image mới (demo tính năng CI/CD)

# SQLite yêu cầu tham số "check_same_thread" đặc thù để cho phép nhiều luồng cùng truy cập; PostgreSQL thì không cần.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Todo(Base):
    """Định nghĩa ORM Model — Ánh xạ trực tiếp với cấu trúc bảng 'todos' trong cơ sở dữ liệu."""
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    done = Column(Boolean, default=False, nullable=False)


# --- Các cấu trúc Pydantic Schemas (Dùng để kiểm tra và xác thực dữ liệu đầu vào/đầu ra) ---
class TodoIn(BaseModel):
    title: str
    done: bool = False


class TodoOut(BaseModel):
    id: int
    title: str
    done: bool
    model_config = {"from_attributes": True}  # Cho phép Pydantic đọc dữ liệu trực tiếp từ các thuộc tính của đối tượng ORM (SQLAlchemy)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tự động khởi tạo bảng dữ liệu khi ứng dụng bắt đầu chạy.
    # LƯU Ý: Đây là giải pháp đơn giản hóa phục vụ cho bài lab. Khi làm dự án thực tế (Production),
    # bạn bắt buộc phải dùng các công cụ quản lý phiên bản database (như Alembic) để thực hiện database migration.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Todo API", lifespan=lifespan)

# Mở CORS (Cross-Origin Resource Sharing) để máy phát triển local (Frontend Vite chạy cổng 9991) có thể gửi request đến Backend.
# Khi triển khai thực tế trên Cluster, cả Frontend và Backend đều chạy chung một domain (được Ingress định tuyến),
# do đó thiết lập cho phép '*' này hoàn toàn vô hại và an toàn.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """API kiểm tra trạng thái hoạt động (Liveness/Readiness Probe của Kubernetes sử dụng API này)."""
    return {"status": "ok"}


@app.get("/api/welcome")
def welcome():
    """API trả về thông điệp chào mừng cấu hình qua biến môi trường (ConfigMap)."""
    return {"message": WELCOME_MESSAGE}


@app.get("/api/version")
def version():
    """API trả về phiên bản hiện tại của ứng dụng (để xác nhận việc cập nhật phiên bản thành công)."""
    return {"version": APP_VERSION}


@app.get("/api/todos", response_model=list[TodoOut])
def list_todos():
    """API truy vấn và trả về toàn bộ danh sách công việc, sắp xếp theo ID tăng dần."""
    with SessionLocal() as db:
        return db.query(Todo).order_by(Todo.id).all()


@app.post("/api/todos", response_model=TodoOut, status_code=201)
def create_todo(payload: TodoIn):
    """API tạo mới một công việc và lưu vào cơ sở dữ liệu."""
    with SessionLocal() as db:
        todo = Todo(title=payload.title, done=payload.done)
        db.add(todo)
        db.commit()
        db.refresh(todo)
        return todo


@app.put("/api/todos/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: int, payload: TodoIn):
    """API cập nhật nội dung hoặc trạng thái hoàn thành của một công việc hiện có."""
    with SessionLocal() as db:
        todo = db.get(Todo, todo_id)
        if todo is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy công việc tương ứng")
        todo.title = payload.title
        todo.done = payload.done
        db.commit()
        db.refresh(todo)
        return todo


@app.delete("/api/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    """API xóa một công việc khỏi cơ sở dữ liệu theo ID."""
    with SessionLocal() as db:
        todo = db.get(Todo, todo_id)
        if todo is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy công việc tương ứng")
        db.delete(todo)
        db.commit()

