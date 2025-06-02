FROM python:3.9-slim-buster
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP app.py
ENV FLASK_ENV production

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# EXPOSE 10000 # এই লাইনটি মুছে ফেলা হয়েছে বা কমেন্ট আউট করা হয়েছে

CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
