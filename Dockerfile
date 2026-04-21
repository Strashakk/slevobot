FROM python:3.12.3-slim

# Avoid writing .pyc files and dump log messages instantly
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Get dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY . .

# Run
CMD ["python", "bot.py"]

