# ZMOBUP — V2Ray Config Speed Tester

ابزار تست کانفیگ‌های V2Ray/Xray از روی لینک Subscription.

## هدف نسخه اول
- دریافت Subscription URL
- Decode کردن Base64 و استخراج کانفیگ‌ها
- پشتیبانی اولیه از VLESS / VMess / Trojan / Shadowsocks
- اجرای هر کانفیگ از طریق Xray
- تست latency، دانلود و آپلود
- ثبت نتیجه هر کانفیگ
- مرتب‌سازی و جدا کردن بهترین کانفیگ‌ها
- خروجی CSV و JSON

## ساختار
```text
ZMOBUP/
  app.py
  requirements.txt
  settings.json
  README.md
  results/
  runtime/
  xray/
```

## مرحله فعلی
نسخه 0.1: اسکلت پروژه و قرارداد تنظیمات.

در مرحله بعد موتور Subscription و سپس موتور Xray/Speed Test اضافه می‌شود.

## نکته
برای تست واقعی ترافیک، Xray executable باید روی سیستم موجود باشد.
