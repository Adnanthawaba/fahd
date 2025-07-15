# دليل التثبيت والتشغيل - Yemen Qaat Installation Guide

## 🖥️ متطلبات النظام - System Requirements

### الحد الأدنى - Minimum Requirements:
- **نظام التشغيل**: Windows 10, macOS 10.14, Ubuntu 18.04 أو أحدث
- **المعالج**: Intel Core i3 أو AMD Ryzen 3
- **الذاكرة**: 4 GB RAM
- **التخزين**: 2 GB مساحة فارغة
- **الشبكة**: اتصال إنترنت للتحديثات

### الموصى به - Recommended:
- **المعالج**: Intel Core i5 أو AMD Ryzen 5
- **الذاكرة**: 8 GB RAM
- **التخزين**: 5 GB مساحة فارغة
- **الشبكة**: اتصال إنترنت سريع

## 📥 التحميل والتثبيت - Download & Installation

### 1. تحميل الملفات المطلوبة:

#### Python (مطلوب):
- **Windows**: تحميل من [python.org](https://python.org/downloads/)
- **macOS**: `brew install python3` أو من الموقع الرسمي
- **Ubuntu/Linux**: `sudo apt install python3 python3-pip`

#### Node.js (للتطوير فقط):
- تحميل من [nodejs.org](https://nodejs.org/)

### 2. استخراج ملفات التطبيق:
```bash
# استخراج الملفات
unzip yemen_qaat_complete_package.zip
cd yemen_qaat_deployment
```

## 🚀 التشغيل السريع - Quick Start

### الطريقة الأولى: استخدام السكريبت التلقائي

#### على Windows:
```cmd
cd yemen_qaat_deployment\server
python run_server.py
```

#### على macOS/Linux:
```bash
cd yemen_qaat_deployment/server
python3 run_server.py
```

### الطريقة الثانية: التشغيل اليدوي

#### 1. تثبيت المتطلبات:
```bash
cd yemen_qaat_deployment/server
pip install -r requirements.txt
```

#### 2. تشغيل الخادم:
```bash
cd src
python main.py
```

## 🌐 الوصول للتطبيق - Accessing the Application

### للمستخدمين العاديين:
- افتح المتصفح واذهب إلى: `http://localhost:5000`
- أو: `http://127.0.0.1:5000`

### للإدارة:
- الرابط المباشر: `http://localhost:5000/?admin=true`
- أو النقر 7 مرات سريعة على شعار التطبيق

**بيانات تسجيل الدخول للإدارة:**
- اسم المستخدم: `admin_yemen_qaat`
- كلمة المرور: `YQ@dm1n2025!`
- رمز الأمان: `2025`

## 📱 التشغيل على الهاتف المحمول - Mobile Access

### 1. الوصول عبر الشبكة المحلية:
```bash
# معرفة عنوان IP الخاص بك
# Windows:
ipconfig

# macOS/Linux:
ifconfig
```

### 2. الوصول من الهاتف:
- افتح المتصفح في الهاتف
- اذهب إلى: `http://[YOUR_IP]:5000`
- مثال: `http://192.168.1.100:5000`

### 3. إضافة للشاشة الرئيسية:
1. افتح التطبيق في متصفح الهاتف
2. اضغط على قائمة المتصفح
3. اختر "إضافة للشاشة الرئيسية"

## ⚙️ الإعدادات المتقدمة - Advanced Configuration

### تغيير منفذ الخادم:
```python
# في ملف src/main.py
app.run(host='0.0.0.0', port=8080, debug=False)
```

### تفعيل HTTPS:
```python
# إضافة شهادة SSL
app.run(host='0.0.0.0', port=443, ssl_context='adhoc')
```

### إعدادات قاعدة البيانات:
```python
# في ملف src/main.py
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///custom_path/app.db'
```

## 🔧 استكشاف الأخطاء - Troubleshooting

### خطأ: "Python not found"
```bash
# تأكد من تثبيت Python
python --version
# أو
python3 --version

# إذا لم يكن مثبتاً، قم بتثبيته من python.org
```

### خطأ: "pip not found"
```bash
# Windows:
python -m ensurepip --upgrade

# macOS/Linux:
sudo apt install python3-pip
```

### خطأ: "Port already in use"
```bash
# إيقاف العملية التي تستخدم المنفذ
# Windows:
netstat -ano | findstr :5000
taskkill /PID [PID_NUMBER] /F

# macOS/Linux:
lsof -ti:5000 | xargs kill -9
```

### خطأ: "Database locked"
```bash
# إعادة تشغيل الخادم
# أو حذف ملف قاعدة البيانات وإعادة إنشائها
rm src/database/app.db
python src/main.py
```

### خطأ: "Module not found"
```bash
# تثبيت المتطلبات مرة أخرى
pip install -r requirements.txt --force-reinstall
```

## 🔄 التحديث والصيانة - Updates & Maintenance

### إنشاء نسخة احتياطية:
```bash
# نسخ قاعدة البيانات
cp src/database/app.db backup_$(date +%Y%m%d_%H%M%S).db

# نسخ الملفات المرفوعة
cp -r src/uploads backup_uploads_$(date +%Y%m%d_%H%M%S)
```

### استعادة النسخة الاحتياطية:
```bash
# استعادة قاعدة البيانات
cp backup_YYYYMMDD_HHMMSS.db src/database/app.db

# استعادة الملفات المرفوعة
cp -r backup_uploads_YYYYMMDD_HHMMSS src/uploads
```

### تنظيف الملفات المؤقتة:
```bash
# حذف ملفات الكاش
rm -rf __pycache__
rm -rf .pytest_cache
rm -rf *.pyc
```

## 🌐 النشر على الإنترنت - Internet Deployment

### 1. استخدام خدمات الاستضافة:

#### Heroku:
```bash
# إنشاء ملف Procfile
echo "web: python src/main.py" > Procfile

# رفع للـ Heroku
git init
git add .
git commit -m "Initial commit"
heroku create yemen-qaat-app
git push heroku main
```

#### DigitalOcean/AWS:
```bash
# تثبيت على خادم Ubuntu
sudo apt update
sudo apt install python3 python3-pip nginx
pip3 install -r requirements.txt

# إعداد Nginx
sudo nano /etc/nginx/sites-available/yemen-qaat
```

### 2. إعداد اسم النطاق:
- شراء نطاق من مزود الخدمة
- ربط النطاق بعنوان IP الخادم
- إعداد شهادة SSL

## 📊 المراقبة والأداء - Monitoring & Performance

### مراقبة استخدام الموارد:
```bash
# مراقبة استخدام المعالج والذاكرة
top
htop

# مراقبة مساحة القرص
df -h

# مراقبة الشبكة
netstat -tuln
```

### تحسين الأداء:
```python
# في ملف src/main.py
# تفعيل الضغط
from flask_compress import Compress
Compress(app)

# تفعيل التخزين المؤقت
from flask_caching import Cache
cache = Cache(app)
```

## 🔐 الأمان والحماية - Security

### تغيير كلمات المرور الافتراضية:
```python
# في ملف src/pages/AdminLoginPage.jsx
const ADMIN_CREDENTIALS = {
    username: 'your_new_username',
    password: 'your_strong_password',
    securityCode: 'your_security_code'
};
```

### تفعيل HTTPS:
```bash
# إنشاء شهادة SSL
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

### إعداد جدار الحماية:
```bash
# Ubuntu/Linux
sudo ufw enable
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
```

## 📞 الدعم الفني - Technical Support

### معلومات مفيدة للدعم:
- **إصدار Python**: `python --version`
- **نظام التشغيل**: `uname -a` (Linux/macOS) أو `systeminfo` (Windows)
- **رسائل الخطأ**: انسخ رسالة الخطأ كاملة
- **ملفات السجل**: تحقق من `logs/` إن وجدت

### طرق التواصل:
- **البريد الإلكتروني**: support@yemenqaat.com
- **الهاتف**: +967-1-234567
- **الموقع**: www.yemenqaat.com

---

**نتمنى لك تجربة ناجحة مع تطبيق يمن قاعات! 🇾🇪**

