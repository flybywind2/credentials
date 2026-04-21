FROM python:3.10.19-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:///./dev.db

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
