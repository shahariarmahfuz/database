# একটি অফিসিয়াল পাইথন রানটাইমকে বেস ইমেজ হিসেবে ব্যবহার করুন
FROM python:3.9-slim-buster

# এনভায়রনমেন্ট ভেরিয়েবল
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP app.py
ENV FLASK_ENV production # Render.com এ এটি production হওয়াই ভালো
# PORT এনভায়রনমেন্ট ভেরিয়েবল Render নিজে থেকে সেট করে দেয় (সাধারণত 10000)

WORKDIR /app

# সিস্টেম নির্ভরতা এবং postgresql-client ইনস্টল করুন
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render.com সাধারণত /var/data বা এই ধরনের কোনো পাথে persistent disk মাউন্ট করে।
# আপনার USER_FILES_BASE_DIR এবং SQLite ডাটাবেজের পাথ (যদি ব্যবহার করতেন) সেই অনুযায়ী সেট করতে হবে
# অথবা Render এর দেওয়া পাথ ব্যবহার করতে হবে।
# আপাতত, ধরে নিচ্ছি USER_FILES_BASE_DIR এবং UPLOAD_FOLDER অ্যাপের রুটের সাথে সম্পর্কিত
# এবং Render Disks আপনি আপনার অ্যাপের ফাইল সিস্টেমের কোনো নির্দিষ্ট পাথে মাউন্ট করবেন।

EXPOSE 10000 # Render সাধারণত 10000 পোর্ট ব্যবহার করে

# ডাটাবেজ টেবিল তৈরি করার জন্য (Render এর deploy script এ এটি যোগ করা যেতে পারে)
# RUN flask init-db 
# অথবা অ্যাপ চালু হওয়ার সময় এটি নিশ্চিত করা হয় app.py তে।

# প্রোডাকশনের জন্য Gunicorn ব্যবহার করা হচ্ছে
# PORT এনভায়রনমেন্ট ভেরিয়েবল Render দ্বারা সেট করা হবে
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
