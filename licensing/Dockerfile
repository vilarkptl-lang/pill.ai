FROM python:3.12-slim
WORKDIR /app
COPY licensing/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY licensing/ ./licensing/
ENV DATABASE_URL=/data/licenses.db
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "licensing.server:app", "--host", "0.0.0.0", "--port", "8080"]
