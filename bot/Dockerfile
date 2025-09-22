FROM python:3.9-slim

WORKDIR /app

# Копируем requirements.txt сначала для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы
COPY . .

CMD ["python", "bot.py"]