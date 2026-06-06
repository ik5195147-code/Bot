# Bot Hosting Panel 🤖

একটি সম্পূর্ণ বট হোস্টিং প্যানেল যা FastAPI দ্বারা তৈরি। এতে রয়েছে লগইন, রেজিস্ট্রেশন, বট ম্যানেজমেন্ট, ফাইল হ্যান্ডলিং এবং লাইভ লগ কনসোল।

## বৈশিষ্ট্য 🎯

- ✅ **ব্যবহারকারী অথেন্টিকেশন**: লগইন এবং রেজিস্ট্রেশন সিস্টেম
- ✅ **বট ম্যানেজমেন্ট**: বট তৈরি, স্টার্ট, স্টপ, এবং রিস্টার্ট
- ✅ **ফাইল ম্যানেজমেন্ট**: ফাইল আপলোড, ডাউনলোড, ডিলিট, এবং এডিট
- ✅ **ZIP ফাইল সাপোর্ট**: ZIP ফাইল আনজিপ করুন
- ✅ **লাইভ লগ কনসোল**: রিয়েল-টাইম লগ দেখুন
- ✅ **ওয়েবসকেট সাপোর্ট**: লাইভ ডেটা আপডেট
- ✅ **সুরক্ষা**: JWT টোকেন বেসড অথেন্টিকেশন

## ইনস্টলেশন 📦

### প্রয়োজনীয় প্যাকেজ ইনস্টল করুন

```bash
pip install -r requirements.txt
```

### বা ম্যানুয়ালি ইনস্টল করুন

```bash
pip install fastapi==0.104.1
pip install uvicorn==0.24.0
pip install python-multipart==0.0.6
pip install pydantic==2.5.0
pip install python-jose==3.3.0
pip install passlib==1.7.4
pip install python-dotenv==1.0.0
pip install aiofiles==23.2.1
pip install websockets==12.0
pip install PyJWT==2.13.0
pip install cryptography==48.0.0
pip install requests==2.34.2
```

## চালু করা 🚀

```bash
python main.py
```

অথবা

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## ব্যবহার 📖

1. **রেজিস্ট্রেশন**: নতুন অ্যাকাউন্ট তৈরি করুন
2. **লগইন**: আপনার অ্যাকাউন্টে প্রবেশ করুন
3. **বট তৈরি করুন**: "New Bot" এ ক্লিক করুন
4. **ফাইল আপলোড করুন**: আপনার বট কোড আপলোড করুন
5. **বট চালান**: "Start" বোতাম দিয়ে বট শুরু করুন
6. **লগ দেখুন**: "Logs" ট্যাবে লাইভ লগ দেখুন

## API এন্ডপয়েন্ট 🔌

### অথেন্টিকেশন
- `POST /api/register` - নতুন ব্যবহারকারী তৈরি করুন
- `POST /api/login` - লগইন করুন
- `GET /api/me` - বর্তমান ব্যবহারকারী তথ্য

### বট ম্যানেজমেন্ট
- `POST /api/bots/{bot_name}/start` - বট শুরু করুন
- `POST /api/bots/{bot_name}/stop` - বট বন্ধ করুন
- `POST /api/bots/{bot_name}/restart` - বট রিস্টার্ট করুন
- `GET /api/bots/{bot_name}/status` - বট স্ট্যাটাস দেখুন

### ফাইল ম্যানেজমেন্ট
- `POST /api/bots/{bot_name}/upload` - ফাইল আপলোড করুন
- `GET /api/bots/{bot_name}/files` - ফাইল লিস্ট দেখুন
- `GET /api/bots/{bot_name}/files/{file_path}` - ফাইল কন্টেন্ট পড়ুন
- `PUT /api/bots/{bot_name}/files/{file_path}` - ফাইল এডিট করুন
- `DELETE /api/bots/{bot_name}/files/{file_path}` - ফাইল ডিলিট করুন
- `POST /api/bots/{bot_name}/unzip` - ZIP ফাইল আনজিপ করুন

### লগ এবং স্ট্রিমিং
- `WS /ws/logs/{bot_name}` - লাইভ লগ স্ট্রিম (WebSocket)

## ডিরেক্টরি স্ট্রাকচার 📁

```
bot-hosting-panel/
├── main.py                 # FastAPI মেইন ফাইল
├── requirements.txt        # পাইথন ডিপেন্ডেন্সি
├── .env                    # এনভায়রনমেন্ট কনফিগুরেশন
├── static/
│   └── index.html         # ফ্রন্টএন্ড
├── bots/                  # বটস স্টোরেজ ডিরেক্টরি
├── logs/                  # লগস স্টোরেজ ডিরেক্টরি
└── bot_panel.db           # SQLite ডাটাবেস
```

## উন্নত বৈশিষ্ট্য 🔧

### কাস্টম বট স্ক্রিপ্ট তৈরি করুন

আপনার বট ডিরেক্টরিতে `main.py` তৈরি করুন:

```python
# bots/username/my-bot/main.py
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

while True:
    logger.info("Bot is running...")
    time.sleep(1)
```

## নিরাপত্তা ⚠️

- SECRET_KEY পরিবর্তন করুন `.env` ফাইলে
- উৎপাদনে HTTPS ব্যবহার করুন
- শক্তিশালী পাসওয়ার্ড ব্যবহার করুন
- নিয়মিত ডাটাবেস ব্যাকআপ নিন

## সমস্যা সমাধান 🐛

### বট শুরু না হলে
- লগস দেখুন `/logs/` ডিরেক্টরিতে
- Python পাথ সঠিক আছে কিনা চেক করুন
- ফাইল পারমিশন চেক করুন

### ফাইল আপলোড না হলে
- `static/` এবং `bots/` ডিরেক্টরি অনুমতি চেক করুন
- ডিস্ক স্পেস চেক করুন

## লাইসেন্স 📄

MIT License

## সাপোর্ট 💬

সমস্যা হলে GitHub issues এ রিপোর্ট করুন।
