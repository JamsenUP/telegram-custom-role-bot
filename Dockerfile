FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Настройка портов и вывода логов
ENV PYTHONUNBUFFERED=1
ENV PORT=10000
EXPOSE 10000

CMD ["python", "main.py"]
