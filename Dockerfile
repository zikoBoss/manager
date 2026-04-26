FROM python:3.12-slim
WORKDIR /app
# نسخ ملف المتطلبات وتثبيتها أولاً (للاستفادة من طبقات التخزين المؤقت)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# نسخ باقي المشروع
COPY . .
# تشغيل البوت
CMD ["python", "main.py"]
