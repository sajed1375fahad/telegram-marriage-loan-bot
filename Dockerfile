FROM python:3.11-slim

WORKDIR /app

# نصب dependencies سیستم
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ایجاد دایرکتوری برای لاگ‌ها
RUN mkdir -p /app/logs

CMD ["python", "app.py"]
