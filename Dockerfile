FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Переменная для вывода логов в реальном времени
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
