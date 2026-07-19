FROM python:3.12-slim

# Keep Python output unbuffered and store the SQLite DB inside the image dir.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE=/app/app.db

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source.
COPY . .

EXPOSE 5000

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
