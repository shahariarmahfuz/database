# একটি অফিসিয়াল পাইথন রানটাইমকে বেস ইমেজ হিসেবে ব্যবহার করুন
FROM python:3.9-slim-buster

# এনভায়রনমেন্ট ভেরিয়েबल
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP app.py
ENV FLASK_ENV production # Render.com এ এটি production হওয়াই ভালো
# PORT এনভায়রনমেন্ট ভেরিয়েবল Render নিজে থেকে সেট করে দেয়

WORKDIR /app

# সিস্টেম নির্ভরতা এবং postgresql-client ইনস্টল করুন
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client build-essential && \
    rm -rf /var/lib/apt/lists/*

# requirements.txt ফাইলটি কন্টেইনারে কপি করুন
COPY requirements.txt .

# requirements.txt এ থাকা পাইথন প্যাকেজগুলো ইনস্টল করুন
RUN pip install --no-cache-dir -r requirements.txt

# আপনার অ্যাপ্লিকেশনের বাকি সব কোড কন্টেইনারে কপি করুন
COPY . .

# EXPOSE লাইনটি বাদ দেওয়া হয়েছে, কারণ Render $PORT ভেরিয়েবল ব্যবহার করে
# এবং Gunicorn সরাসরি সেই $PORT এ বাইন্ড করবে।

# প্রোডাকশনের জন্য Gunicorn ব্যবহার করা হচ্ছে
# PORT এনভায়রনমেন্ট ভেরিয়েবল Render দ্বারা সেট করা হবে
# WORKERS এর সংখ্যা আপনার Render প্ল্যানের রিসোর্স অনুযায়ী সেট করতে পারেন (সাধারণত 2-4)
# THREADS প্রতি ওয়ার্কারের জন্য (Gunicorn এর ডিফল্ট ১, তবে I/O বাউন্ড অ্যাপের জন্য বেশি হতে পারে)
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
