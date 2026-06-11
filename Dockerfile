# ---- Stage 1: cai dependency ----
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
# Cai thu vien vao mot prefix rieng de stage sau chi copy ket qua.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Stage 2: runtime gon ----
FROM python:3.12-slim
WORKDIR /app
# Copy thu vien da cai tu stage builder (khong mang theo cong cu build).
COPY --from=builder /install /usr/local
COPY . .
# Tao user non-root va cho phep ghi vao /app (vd file SQLite luc test local).
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 8882
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8882"]
