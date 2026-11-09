# WASELNI Backend (Django + Django REST Framework + Channels)

هذا المستودع مخصص للـ Backend المركزي المشترك لتطبيقات Customer وCaptain وMerchant وAdmin.

## تشغيل محلي

1. أنشئ بيئة افتراضية وثبّت المتطلبات:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\\Scripts\\activate
   # macOS/Linux:
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. انسخ `.env.example` إلى `.env` وعدّل القيم المحلية.
3. نفّذ:
   ```bash
   python manage.py migrate
   python manage.py check
   python manage.py runserver
   ```

## Render (Web Service)

- Root Directory: `.` (جذر هذا المستودع).
- Runtime: Python.
- Build Command: `pip install -r requirements.txt`
- Start Command: `daphne -b 0.0.0.0 -p $PORT config.asgi:application`
- أضف PostgreSQL وأنشئ `DATABASE_URL` باستخدام عنوان الاتصال الداخلي.
- أضف Redis متوافقاً مع Channels واضبط `REDIS_URL`.
- اضبط `DEBUG=False`.
- أنشئ `SECRET_KEY` عشوائياً وفريداً في إعدادات Render؛ لا تضعه في GitHub.
- اضبط `ALLOWED_HOSTS` على نطاق خدمة Render فقط.
- اضبط `CORS_ALLOWED_ORIGINS` على نطاقات Vercel الأربعة فقط.
- اضبط `CSRF_TRUSTED_ORIGINS` على نطاقات HTTPS الفعلية عند الحاجة.
- اضبط `ROUTING_BASE_URL` على مزود التوجيه المعتمد.
- اضبط تخزيناً دائماً/خارجياً للملفات المرفوعة؛ نظام ملفات الخدمة ليس بديلاً عن تخزين دائم.

## تنبيه قبل الإنتاج

لا تعتبر الخدمة جاهزة للإنتاج قبل تشغيل `python manage.py check --deploy`،
والاختبارات، والتحقق من إعدادات CORS/Hosts وPostgreSQL وRedis والتخزين الدائم.
لا ترفع `.env` أو `db.sqlite3` أو مجلد `media/` أو أي مفاتيح سرية إلى GitHub.
