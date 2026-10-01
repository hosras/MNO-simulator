## یک دستور PowerShell — نوشتن کل راهنما در یک فایل

این را در PowerShell کپی و اجرا کن (از هر پوشه‌ای):

```powershell
cd D:\simulation\mci; $content = @'
# راهنمای کامل TELECOM-NET-SIM Suite

شبیه‌ساز شبکه اپراتوری همراه با پشتیبانی از 2G/3G/4G/5G/6G، شبیه‌سازی حملات، تحلیل‌های آماری و پنل مدیریت CRUD.

---

## فهرست مطالب

1. ساختار پروژه
2. شروع سریع
3. دستورات روزمره
4. بررسی سلامت سیستم
5. Snapshot گرفتن (پشتیبان‌گیری)
6. بازگردانی از Snapshot
7. بازسازی از صفر
8. ابزارهای تعمیر
9. عیب‌یابی
10. نگهداری و Maintenance
11. دستورات تک‌خطی مفید
12. چک‌لیست روزمره

---

## ۱) ساختار پروژه

```
D:\simulation\mci\
├── telecom_common.py        # ماژول مشترک (توابع، ثابت‌ها، احراز هویت)
├── telecom_net_sim.py       # شبیه‌ساز شبکه (2G/3G/4G/5G/6G + 2PB)
├── telecom_attack.py        # ماژول شبیه‌سازی حمله (۲۴ سناریو شامل 6G)
├── telecom_dashboard.py     # داشبورد مدیریتی (Streamlit)
├── telecom_radar.py         # تحلیل‌های آماری (Streamlit)
├── telecom_admin.py         # پنل ادمین CRUD (Streamlit)
├── check_db.py              # بررسی صحت دیتابیس
├── check_6g_now.py          # بررسی حضور 6G
├── restore_2pb.py           # بازگرداندن ترافیک ۲ پتابایت
└── telecom_sim_output\      # پوشه خروجی
    ├── telecom_sim.db       # دیتابیس اصلی SQLite
    ├── backups\             # بکاپ‌های داخلی دیتابیس
    └── *.png, report.txt    # نمودارها و گزارش
```

### وضعیت فعلی (تأییدشده)

| شاخص                    | مقدار      |
|-------------------------|------------|
| سلول‌های 6G             | ۱۵         |
| گره‌های هسته 6G         | ۱۱         |
| تماس‌های Vo6G           | ۱٬۴۴۱      |
| CDR روی سلول‌های 6G     | ۲٬۹۷۲      |
| سناریوهای حمله 6G       | ۵ یا بیشتر |
| مجموع ترافیک            | ۲.۰۰ PB    |

---

## ۲) شروع سریع

### قدم ۱ — رفتن به پوشه پروژه

```powershell
cd D:\simulation\mci
```

### قدم ۲ — ساخت دیتابیس از صفر (در صورت نیاز)

```powershell
python telecom_net_sim.py
python telecom_attack.py
```

### قدم ۳ — اجرای سه اپلیکیشن Streamlit

سه ترمینال PowerShell جدا باز کن و در هر کدام یکی از این‌ها را اجرا کن:

ترمینال ۱ — داشبورد:
```powershell
cd D:\simulation\mci
streamlit run telecom_dashboard.py --server.port 8501
```

ترمینال ۲ — رادار:
```powershell
cd D:\simulation\mci
streamlit run telecom_radar.py --server.port 8502
```

ترمینال ۳ — ادمین:
```powershell
cd D:\simulation\mci
streamlit run telecom_admin.py --server.port 8503
```

### قدم ۴ — باز کردن در مرورگر

| اپ        | آدرس                    |
|-----------|-------------------------|
| داشبورد   | http://localhost:8501   |
| رادار     | http://localhost:8502   |
| ادمین     | http://localhost:8503   |

برای بستن هر اپ: در ترمینال مربوطه Ctrl+C بزن.

---

## ۳) دستورات روزمره

### رفتن به پوشه پروژه

```powershell
cd D:\simulation\mci
```

### ساخت دیتابیس از صفر

```powershell
python telecom_net_sim.py       # شبکه + 6G + 2PB خودکار
python telecom_attack.py        # سناریوهای حمله (شامل 6G)
```

### اجرای سه اپ (در سه ترمینال جدا)

```powershell
# ترمینال ۱
streamlit run telecom_dashboard.py --server.port 8501

# ترمینال ۲
streamlit run telecom_radar.py --server.port 8502

# ترمینال ۳
streamlit run telecom_admin.py --server.port 8503
```

---

## ۴) بررسی سلامت سیستم

### بررسی کلی دیتابیس

```powershell
python check_db.py
```

### بررسی دقیق 6G

```powershell
python check_6g_now.py
```

### چک سریع مجموع ترافیک

```powershell
python -c "import sqlite3; c=sqlite3.connect('telecom_sim_output/telecom_sim.db'); print('Total PB:', round(c.execute('SELECT SUM(bytes) FROM cdrs').fetchone()[0]/1e15, 2))"
```

### چک تعداد سلول‌های 6G

```powershell
python -c "import sqlite3; c=sqlite3.connect('telecom_sim_output/telecom_sim.db'); print('6G cells:', c.execute(\"SELECT COUNT(*) FROM cells WHERE tech='6G'\").fetchone()[0])"
```

### چک تماس‌های Vo6G

```powershell
python -c "import sqlite3; c=sqlite3.connect('telecom_sim_output/telecom_sim.db'); print('Vo6G:', c.execute(\"SELECT COUNT(*) FROM cdrs WHERE voice_bearer='Vo6G'\").fetchone()[0])"
```

### چک سناریوهای حمله 6G

```powershell
python -c "import sqlite3; c=sqlite3.connect('telecom_sim_output/telecom_sim.db'); [print(r) for r in c.execute(\"SELECT attack_type, severity, status FROM attack_scenarios WHERE target_layer='6G'\").fetchall()]"
```

### چک توزیع Bearer صوتی

```powershell
python -c "import sqlite3; c=sqlite3.connect('telecom_sim_output/telecom_sim.db'); [print(r) for r in c.execute('SELECT voice_bearer, COUNT(*) FROM cdrs WHERE call_type=\"voice\" GROUP BY voice_bearer').fetchall()]"
```

---

## ۵) Snapshot گرفتن (پشتیبان‌گیری)

### چرا Snapshot؟

هر بار که telecom_net_sim.py اجرا کنی، دیتابیس از صفر ساخته می‌شود. CDRها، alertها و تغییرات دستی از بین می‌روند. قبل از هر عملیات مخرب یا بعد از رسیدن به یک وضعیت پایدار، Snapshot بگیر.

### ۵.۱ — Snapshot کامل پروژه (کد + دیتابیس)

```powershell
cd D:\simulation\mci
Compress-Archive -Path *.py,telecom_sim_output -DestinationPath "telecom_backup_$(Get-Date -Format 'yyyyMMdd_HHmm').zip"
```

خروجی نمونه: telecom_backup_20260926_1245.zip

### ۵.۲ — فقط کد

```powershell
cd D:\simulation\mci
Compress-Archive -Path *.py -DestinationPath "telecom_code_$(Get-Date -Format 'yyyyMMdd_HHmm').zip"
```

### ۵.۳ — فقط دیتابیس

```powershell
cd D:\simulation\mci
Compress-Archive -Path telecom_sim_output -DestinationPath "telecom_db_$(Get-Date -Format 'yyyyMMdd_HHmm').zip"
```

### ۵.۴ — در پوشه مخصوص snapshots

```powershell
cd D:\simulation\mci
New-Item -ItemType Directory -Force -Path "snapshots" | Out-Null
Compress-Archive -Path *.py,telecom_sim_output -DestinationPath "snapshots\snap_$(Get-Date -Format 'yyyyMMdd_HHmm').zip"
```

### ۵.۵ — Snapshot با تگ (تعاملی)

```powershell
cd D:\simulation\mci
$tag = Read-Host "یک تگ کوتاه برای این snapshot بنویس (مثل stable یا pre-6g)"
Compress-Archive -Path *.py,telecom_sim_output -DestinationPath "snapshots\snap_$tag`_$(Get-Date -Format 'yyyyMMdd_HHmm').zip"
```

### ۵.۶ — لیست کردن همه snapshotها

```powershell
Get-ChildItem snapshots\*.zip | Sort-Object LastWriteTime -Descending |
  Select-Object Name,
    @{N='Size (MB)';E={[math]::Round($_.Length/1MB,2)}},
    LastWriteTime
```

### ۵.۷ — حذف snapshotهای قدیمی (نگه‌داشتن ۱۰ تای آخر)

```powershell
Get-ChildItem snapshots\*.zip |
  Sort-Object LastWriteTime -Descending |
  Select-Object -Skip 10 |
  Remove-Item -Force
```

---

## ۶) بازگردانی از Snapshot

### ۶.۱ — لیست snapshotها

```powershell
cd D:\simulation\mci
Get-ChildItem snapshots\*.zip
```

### ۶.۲ — انتقال پروژه فعلی به پوشه ایمنی (احتیاط)

```powershell
cd D:\simulation\mci
$ts = Get-Date -Format 'yyyyMMdd_HHmm'
New-Item -ItemType Directory -Force -Path "_before_restore_$ts" | Out-Null
Move-Item *.py,telecom_sim_output -Destination "_before_restore_$ts"
```

### ۶.۳ — باز کردن snapshot

```powershell
cd D:\simulation\mci
Expand-Archive -Path "snapshots\snap_XXXX.zip" -DestinationPath "." -Force
```

مثال عینی:

```powershell
Expand-Archive -Path "snapshots\snap_stable_20260926_1245.zip" -DestinationPath "." -Force
```

### ۶.۴ — بررسی صحت

```powershell
python check_db.py
python check_6g_now.py
```

### ۶.۵ — اگر همه‌چیز درست بود، پوشه ایمنی را پاک کن

```powershell
Remove-Item -Recurse -Force "_before_restore_*"
```

### ۶.۶ — اگر مشکل داشت، از پوشه ایمنی برگردان

```powershell
$bak = Get-ChildItem -Directory -Filter "_before_restore_*" |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
Copy-Item "$($bak.FullName)\*" -Destination . -Recurse -Force
```

### ۶.۷ — بازگردانی کامل در ۳۰ ثانیه

اگر پروژه خراب شد و یک snapshot سالم داری:

```powershell
cd D:\simulation\mci
Remove-Item -Recurse -Force *.py,telecom_sim_output -ErrorAction SilentlyContinue
Expand-Archive -Path "snapshots\snap_XXXX.zip" -DestinationPath "." -Force
python check_db.py
python check_6g_now.py
```

---

## ۷) بازسازی از صفر

اگر پروژه کاملاً خراب شد یا می‌خواهی همه‌چیز را از نو بسازی:

### ۷.۱ — اول snapshot بگیر (احتیاط)

```powershell
cd D:\simulation\mci
Compress-Archive -Path *.py,telecom_sim_output -DestinationPath "snapshots\pre_reset_$(Get-Date -Format 'yyyyMMdd_HHmm').zip"
```

### ۷.۲ — دیتابیس را پاک کن

```powershell
Remove-Item -Recurse -Force telecom_sim_output
```

### ۷.۳ — از نو بساز

```powershell
python telecom_net_sim.py       # DB + 6G + 2PB
python telecom_attack.py        # سناریوهای حمله
```

### ۷.۴ — تأیید نهایی

```powershell
python check_6g_now.py
```

---

## ۸) ابزارهای تعمیر

### بازگرداندن ترافیک به ۲ پتابایت

```powershell
python restore_2pb.py
```

### لیست بکاپ‌های داخلی کد

```powershell
Get-ChildItem *.bak_* | Select-Object Name, LastWriteTime
```

### بازگردانی یک فایل از بکاپ داخلی

```powershell
Copy-Item telecom_net_sim.py.bak_20260926_124133 telecom_net_sim.py -Force
```

### پاک کردن cache Streamlit

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.streamlit\cache" -ErrorAction SilentlyContinue
```

### ریست کامل رمز ادمین

```powershell
Remove-Item "telecom_sim_output\.admin_auth" -Force
Remove-Item "telecom_sim_output\.admin_salt" -Force
```

دفعه بعد که streamlit run telecom_admin.py اجرا کنی، فرم تنظیم رمز جدید می‌آید.

### کشتن پروسه‌های Streamlit گیرکرده

```powershell
Get-Process | Where-Object { $_.ProcessName -like "*streamlit*" } | Stop-Process -Force
```

### پیدا کردن پروسه روی یک پورت

```powershell
netstat -ano | findstr :8501
```

سپس کشتن با PID:

```powershell
taskkill /F /PID XXXX
```

---

## ۹) عیب‌یابی

### ۹.۱ — خطای StreamlitDuplicateElementId

علامت:

```
streamlit.errors.StreamlitDuplicateElementId: There are multiple
`plotly_chart` (یا `download_button`) elements with the same auto-generated ID.
```

علت: دو ویجت با پارامترهای یکسان، شناسه داخلی یکسان می‌سازند.

راه‌حل:

```powershell
# برای نمودارها
python fix_chart_ids.py

# برای دکمه‌های دانلود
python fix_download_ids.py

# سپس اپ مربوطه را restart کن
```

اگر اسکریپت wrapper موجود نیست، دستی به فراخوانی مشکل‌دار key=... اضافه کن.

### ۹.۲ — دیتابیس پیدا نمی‌شود

علامت:

```
sqlite3.OperationalError: unable to open database file
```

علت: اسکریپت از پوشه دیگری اجرا شده، یا دیتابیس ساخته نشده.

راه‌حل:

```powershell
cd D:\simulation\mci
python telecom_net_sim.py
```

همیشه اسکریپت‌ها را از ریشه پروژه اجرا کن.

### ۹.۳ — 6G در دیتابیس نیست

علامت: check_6g_now.py صفر نشان می‌دهد برای سلول‌ها و تماس‌ها.

راه‌حل:

```powershell
python fix_6g_everything.py     # اگر موجود بود
python telecom_net_sim.py
python telecom_attack.py
python check_6g_now.py
```

### ۹.۴ — ترافیک کل صفر شد

علامت: check_db.py مقدار 0.00 PB نشان می‌دهد.

راه‌حل:

```powershell
python restore_2pb.py
```

### ۹.۵ — رمز ادمین فراموش شده

```powershell
Remove-Item "telecom_sim_output\.admin_auth" -Force
Remove-Item "telecom_sim_output\.admin_salt" -Force
```

سپس ادمین را restart کن.

### ۹.۶ — پورت Streamlit اشغال است

علامت:

```
OSError: [Errno 98] Address already in use
```

راه‌حل:

```powershell
netstat -ano | findstr :8501
taskkill /F /PID XXXX
```

یا از پورت دیگری استفاده کن:

```powershell
streamlit run telecom_dashboard.py --server.port 8510
```

### ۹.۷ — خطای KeyError: 'Vo6G'

علت: ورودی Vo6G در دیکشنری VOICE_BEARERS فایل telecom_net_sim.py نیست.

راه‌حل:

```powershell
python fix_6g_everything.py
python telecom_net_sim.py
```

### ۹.۸ — خطای ModuleNotFoundError (pandas)

علت: دیباگر VSCode با مفسر متفاوتی اجرا می‌شود.

راه‌حل: از ترمینال PowerShell معمولی اجرا کن:

```powershell
python telecom_attack.py
```

### ۹.۹ — نمودارها خالی هستند

علت: فیلترهای سایدبار همه داده را حذف کرده‌اند یا cache قدیمی است.

راه‌حل:

1. دکمه «Reload Data» در سایدبار
2. پاک کردن cache:

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.streamlit\cache" -ErrorAction SilentlyContinue
```

3. restart اپ

### ۹.۱۰ — سناریوهای حمله صفر

راه‌حل:

```powershell
python telecom_attack.py
python check_6g_now.py
```

### ۹.۱۱ — پکیج‌های گمشده

```powershell
pip install plotly kaleido pandas streamlit numpy
```

### ۹.۱۲ — مشکل انکودینگ فارسی

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

---

## ۱۰) نگهداری و Maintenance

### جدول Script های تعمیر

| اسکریپت                  | هدف                                          |
|--------------------------|----------------------------------------------|
| fix_6g_everything.py     | افزودن پشتیبانی 6G به sim و common           |
| fix_6g_catalog.py        | تزریق سناریوهای 6G به ATTACK_CATALOG         |
| fix_6g_attacks_final.py  | اجباری کردن 6G در pool حملات                 |
| fix_chart_ids.py         | پوشش st.plotly_chart با key یکتا             |
| fix_download_ids.py      | پوشش st.download_button با key یکتا          |
| restore_2pb.py           | اسکیل دیتابیس فعلی به 2PB                    |

### جدول Script های تشخیصی

| اسکریپت             | هدف                                           |
|---------------------|-----------------------------------------------|
| check_db.py         | تعداد ردیف‌ها، جدول‌ها، KPI های کلیدی          |
| check_6g_now.py     | بررسی عمیق 6G (سلول، گره، تماس، حمله)         |
| diag_attack.py      | چاپ بدنه توابع از telecom_attack.py           |

### خلاصه Schema دیتابیس

| جدول                 | هدف                                          |
|----------------------|----------------------------------------------|
| cells                | موجودی سلول‌ها (2G/3G/4G/5G/6G)               |
| cores                | گره‌های هسته (MSC، MME، AMF، NWDAF، ...)      |
| subscribers          | رکورد مشترکین با دسترسی‌ها                    |
| cdrs                 | رکورد تماس (۶۰٬۰۰۰ در هر اجرا)                |
| alerts               | موتور هشدار + هشدارهای حمله                   |
| sms_alerts           | لاگ ارسال SMS                                |
| audit_log            | لاگ عملیات پنل ادمین                          |
| osint_public_registry| رجیستری عمومی سلول‌ها (OSINT)                 |
| osint_complaints     | شکایات عمومی (OSINT)                          |
| sigint_findings      | نتایج SIGINT به صورت JSON                     |
| attack_scenarios     | متادیتای سناریوهای حمله                       |
| attack_events        | رخدادهای سری زمانی حمله                       |

### نگهداری دوره‌ای

هفتگی:

```powershell
cd D:\simulation\mci
python check_db.py
python check_6g_now.py
```

ماهانه:

```powershell
cd D:\simulation\mci
Compress-Archive -Path *.py,telecom_sim_output -DestinationPath "snapshots\monthly_$(Get-Date -Format 'yyyyMMdd').zip"
```

هنگام بازسازی دیتابیس:

```powershell
python restore_2pb.py       # بازگرداندن 2PB
python telecom_attack.py    # بازتولید سناریوهای حمله
```

### بررسی یکپارچگی

بررسی اینکه هیچ فایل .py خالی نیست:

```powershell
Get-ChildItem *.py | Where-Object { $_.Length -eq 0 }
```

نباید چیزی برگرداند.

### بررسی حمله

```powershell
python -c "import sqlite3; c=sqlite3.connect('telecom_sim_output/telecom_sim.db'); print('Scenarios:', c.execute('SELECT COUNT(*) FROM attack_scenarios').fetchone()[0]); print('Events:', c.execute('SELECT COUNT(*) FROM attack_events').fetchone()[0])"
```

انتظار:

```
Scenarios: 25
Events:    500
```

### لاگ‌گیری (اختیاری)

```powershell
python telecom_net_sim.py *> "logs\sim_$(Get-Date -Format 'yyyyMMdd_HHmm').log"
```

پاک کردن لاگ‌های قدیمی‌تر از ۳۰ روز:

```powershell
Get-ChildItem logs\*.log |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
  Remove-Item -Force
```

---

## ۱۱) دستورات تک‌خطی مفید

### رفتن به پوشه

```powershell
cd D:\simulation\mci
```

### بازسازی همه‌چیز

```powershell
python telecom_net_sim.py ; python telecom_attack.py
```

### اجرای هر سه اپ در پنجره‌های جدید

```powershell
Start-Process powershell -ArgumentList "cd D:\simulation\mci; streamlit run telecom_dashboard.py --server.port 8501"
Start-Process powershell -ArgumentList "cd D:\simulation\mci; streamlit run telecom_radar.py --server.port 8502"
Start-Process powershell -ArgumentList "cd D:\simulation\mci; streamlit run telecom_admin.py --server.port 8503"
```

### بررسی سلامت

```powershell
python check_db.py ; python check_6g_now.py
```

### مجموع ترافیک (PB)

```powershell
python -c "import sqlite3; c=sqlite3.connect('telecom_sim_output/telecom_sim.db'); print(round(c.execute('SELECT SUM(bytes) FROM cdrs').fetchone()[0]/1e15, 3))"
```

### تعداد سلول‌های 6G

```powershell
python -c "import sqlite3; c=sqlite3.connect('telecom_sim_output/telecom_sim.db'); print(c.execute(\"SELECT COUNT(*) FROM cells WHERE tech='6G'\").fetchone()[0])"
```

### تماس‌های Vo6G

```powershell
python -c "import sqlite3; c=sqlite3.connect('telecom_sim_output/telecom_sim.db'); print(c.execute(\"SELECT COUNT(*) FROM cdrs WHERE voice_bearer='Vo6G'\").fetchone()[0])"
```

### بازگرداندن 2PB

```powershell
python restore_2pb.py
```

### ریست رمز ادمین

```powershell
Remove-Item "telecom_sim_output\.admin_auth","telecom_sim_output\.admin_salt" -Force
```

### Snapshot سریع

```powershell
Compress-Archive -Path *.py,telecom_sim_output -DestinationPath "snapshots\snap_$(Get-Date -Format 'yyyyMMdd_HHmm').zip"
```

### بازگردانی Snapshot

```powershell
Expand-Archive -Path "snapshots\snap_XXXX.zip" -DestinationPath "." -Force
```

### لیست بکاپ‌های داخلی

```powershell
Get-ChildItem *.bak_* | Select-Object Name, LastWriteTime
```

### کشتن Streamlit

```powershell
Get-Process | Where-Object { $_.ProcessName -like "*streamlit*" } | Stop-Process -Force
```

### پاک کردن cache Streamlit

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.streamlit\cache"
```

### ریست کامل (مخرب!)

```powershell
Remove-Item -Recurse -Force telecom_sim_output ; python telecom_net_sim.py ; python telecom_attack.py
```

---

## ۱۲) چک‌لیست روزمره

### شروع روز

```powershell
# ۱) رفتن به پوشه
cd D:\simulation\mci

# ۲) بررسی سلامت
python check_db.py
python check_6g_now.py

# ۳) اگر DB نبود یا خراب بود
python telecom_net_sim.py
python telecom_attack.py
python restore_2pb.py

# ۴) اجرای اپ‌ها (در سه ترمینال جدا)
streamlit run telecom_dashboard.py --server.port 8501
streamlit run telecom_radar.py --server.port 8502
streamlit run telecom_admin.py --server.port 8503
```

### پایان روز (اختیاری)

```powershell
# Snapshot از وضعیت پایدار
cd D:\simulation\mci
Compress-Archive -Path *.py,telecom_sim_output -DestinationPath "snapshots\snap_daily_$(Get-Date -Format 'yyyyMMdd').zip"
```

---

## نکات پایانی

1. قبل از هر تغییر مهم، Snapshot بگیر — کم‌هزینه و ارزشمند
2. سه اپ را در سه ترمینال جدا اجرا کن با پورت‌های 8501، 8502، 8503
3. هر بار telecom_net_sim.py اجرا کنی، دیتابیس بازنویسی می‌شود — پس اگر داده‌ی خاصی داری، اول Snapshot بگیر
4. پس از هر بار بازسازی دیتابیس، اگر ترافیک 2PB صفر شد، python restore_2pb.py را اجرا کن
5. نام‌گذاری Snapshotها با تگ (stable، pre-6g، ...) کار بازیابی را راحت می‌کند
6. دیتابیس telecom_sim.db تنها منبع داده است — پاک کردنش همه‌چیز را از بین می‌برد
7. پوشه telecom_sim_output/backups/ بکاپ‌های خودکار داخلی DB را دارد که از پنل ادمین ساخته می‌شوند

---

## ساختار پیشنهادی پس از راه‌اندازی

```
D:\simulation\mci\
├── راهنما.md                  # همین فایل
├── snapshots\                 # zip های پشتیبان
├── logs\                      # لاگ‌های اجرا (اختیاری)
├── archive\                   # فایل‌های قدیمی
├── telecom_common.py
├── telecom_net_sim.py
├── telecom_attack.py
├── telecom_dashboard.py
├── telecom_radar.py
├── telecom_admin.py
├── check_db.py
├── check_6g_now.py
├── restore_2pb.py
└── telecom_sim_output\
    ├── telecom_sim.db
    ├── backups\
    ├── .admin_auth
    ├── .admin_salt
    ├── *.png
    └── report.txt
```

---

پایان راهنما — در صورت بروز هر مشکل، ابتدا check_db.py و check_6g_now.py را اجرا کن و خروجی را بررسی کن. اگر مشکل حل نشد، از Snapshot برگردان.
'@; [System.IO.File]::WriteAllText("D:\simulation\mci\راهنما.md", $content, [System.Text.UTF8Encoding]::new($false)); Write-Host "✓ راهنما.md ساخته شد:"; Get-Item "D:\simulation\mci\راهنما.md" | Select-Object FullName, Length
```

## نکات مهم

| نکته | توضیح |
|---|---|
| **Here-String `@'...'@`** | متن خام بین این دو خط قرار میگیرد؛ متغیرها تفسیر نمیشوند |
| **`[System.IO.File]::WriteAllText`** | با انکودینگ UTF-8 **بدون BOM** ذخیره میکند (برای سازگاری با Markdown) |
| **`$tag`_ با backtick** | در متن، کاراکتر ` را escape میکند تا PowerShell آن را بهعنوان متغیر نگیرد |
| **مسیر کامل** | در هر پوشهای اجرا کنی، فایل در `D:\simulation\mci\راهنما.md` ساخته میشود |

## تأیید بعد از اجرا

باید ببینی:

```
✓ راهنما.md ساخته شد:

FullName                       Length
--------                       ------
D:\simulation\mci\راهنما.md    15234
```

عدد `Length` باید حدود ۱۵٬۰۰۰ بایت یا بیشتر باشد.

## اگر خواستی محتوا را ببینی

```powershell
Get-Content "D:\simulation\mci\راهنما.md" | Select-Object -First 30
```

## اگر خطای «رشته here-string بسته نشده» دیدی

یعنی خط `'@` دقیقاً در ابتدای خط نبوده. مطمئن شو:
- خط پایانی فقط شامل `'@` باشد (بدون فاصله یا tab قبلش)
- کل متن را در یک کپی/پیست کن، نه تکهتکه

بعد از موفقیت، اگر خواستی فایل را در VS Code یا Notepad باز کنی:

```powershell
notepad "D:\simulation\mci\راهنما.md"
```