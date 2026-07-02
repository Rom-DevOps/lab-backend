# ---- Giai đoạn 1: Cài đặt các thư viện phụ thuộc (Dependencies Builder) ----
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
# Cài đặt thư viện vào một thư mục prefix riêng biệt (/install) để giai đoạn sau chỉ cần copy kết quả, loại bỏ các công cụ build.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Giai đoạn 2: Tạo Docker Image chạy thực tế siêu gọn nhẹ ----
FROM python:3.12-slim
WORKDIR /app
# Chỉ copy các thư viện đã được biên dịch/cài đặt thành công từ giai đoạn builder sang.
COPY --from=builder /install /usr/local
COPY . .
# Tạo một tài khoản người dùng thường (non-root) "appuser" và phân quyền sở hữu thư mục ứng dụng.
# Việc chạy ứng dụng dưới quyền non-root là tiêu chuẩn bắt buộc của bảo mật Container để tránh leo thang đặc quyền.
# Đồng thời cấp quyền để ứng dụng ghi được dữ liệu SQLite (todo.db) khi test local.
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 8882
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8882"]

