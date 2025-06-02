# একটি অফিসিয়াল পাইথন রানটাইমকে বেস ইমেজ হিসেবে ব্যবহার করুন
FROM python:3.9-slim-buster

# এনভায়রনমেন্ট ভেরিয়েবল
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP app.py
ENV FLASK_ENV production

WORKDIR /app

# সিস্টেম নির্ভরতা এবং postgresql-client ইনস্টল করুন
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# EXPOSE লাইনটি বাদ দেওয়া হয়েছে

# অ্যাপ্লিকেশন চালানোর কমান্ড - পোর্ট 5000 হার্ডকোড করা হয়েছে
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
