# Build the Vite/React frontend using Node, then serve it with FastAPI.
FROM node:22-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/ /app/backend/
COPY --from=frontend-build /build/frontend/dist/ /app/frontend/dist/
WORKDIR /app/backend
ENV PORT=10000
CMD ["sh","-c","exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
