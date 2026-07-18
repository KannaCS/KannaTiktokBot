# TikTok Live Bot 🤖

Bot AI yang nonton dan berinteraksi di TikTok Live kamu secara otomatis.

## Fitur
- 👁️ Monitor event live: viewer, komentar, gift, like
- 💬 Komentar otomatis dengan AI (OpenAI GPT-4o-mini)
- 🔁 Balas komentar penonton lain secara natural
- 🎁 Bereaksi saat ada yang kirim gift
- ⏱️ Rate limiting otomatis biar tidak kena ban
- 🔄 Auto-restart via systemd

---

## ⚠️ Batasan Penting: Posting Komentar

**Library `TikTokLive` hanya bisa MEMBACA event** (read-only). 
Bot ini bisa mendeteksi semua yang terjadi di live, tapi untuk **posting komentar** ada beberapa opsi:

### Opsi 1: TikTok Creator API (Resmi, Direkomendasikan)
- Daftar di https://developers.tiktok.com/
- Minta akses ke Live API
- Butuh proses approval (bisa memakan waktu)

### Opsi 2: Ayrshare API (Third-party, Berbayar)
- Service yang punya akses TikTok API
- Lebih mudah setup, tapi ada biaya

### Opsi 3: Selenium Browser Automation (Tidak Direkomendasikan)
- Otomatisasi browser untuk klik tombol komentar
- Rawan kena ban, tidak stabil

**Untuk sekarang**, bot ini akan log semua komentar yang "ingin dikirim" ke `bot.log`.
Kamu bisa implementasi `_post_comment()` di `tiktok_bot.py` sesuai opsi yang dipilih.

---

## Setup di Ubuntu Server

### 1. Clone/upload project
```bash
# Upload files ke server
scp -r tiktok-bot/ ubuntu@IP_SERVER:/home/ubuntu/

# Atau kalau pakai git
git clone <repo-url> /home/ubuntu/tiktok-bot
```

### 2. Install dependencies
```bash
cd /home/ubuntu/tiktok-bot

# Buat virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 3. Setup konfigurasi
```bash
cp .env.example .env
nano .env  # Isi dengan nilai yang benar
```

### 4. Test jalankan
```bash
source venv/bin/activate
python main.py
```

### 5. Deploy sebagai systemd service (jalan terus di background)
```bash
# Copy service file
sudo cp tiktok-bot.service /etc/systemd/system/

# Edit path jika username server bukan 'ubuntu'
sudo nano /etc/systemd/system/tiktok-bot.service

# Reload systemd dan aktifkan
sudo systemctl daemon-reload
sudo systemctl enable tiktok-bot
sudo systemctl start tiktok-bot

# Cek status
sudo systemctl status tiktok-bot

# Lihat log real-time
sudo journalctl -u tiktok-bot -f
```

### 6. Perintah berguna
```bash
# Stop bot
sudo systemctl stop tiktok-bot

# Restart bot
sudo systemctl restart tiktok-bot

# Lihat log bot
tail -f /home/ubuntu/tiktok-bot/bot.log
```

---

## Konfigurasi (.env)

| Variable | Default | Keterangan |
|---|---|---|
| `TIKTOK_USERNAME` | - | Username TikTok kamu (tanpa @) |
| `GROQ_API_KEY` | - | API key dari Groq (console.groq.com) |
| `BOT_PERSONA_NAME` | Andi | Nama persona bot |
| `BOT_LANGUAGE` | id | `id` = Indonesia, `en` = English |
| `COMMENT_MIN_INTERVAL` | 30 | Jeda minimum antar komentar (detik) |
| `COMMENT_MAX_INTERVAL` | 90 | Jeda maksimum antar komentar (detik) |
| `REPLY_TO_COMMENTS` | true | Bot balas komentar orang? |
| `MAX_REPLIES_PER_MINUTE` | 2 | Max reply per menit |

---

## Struktur Project
```
tiktok-bot/
├── main.py           # Entry point
├── config.py         # Konfigurasi dan env vars
├── ai_responder.py   # Logic AI (OpenAI)
├── tiktok_bot.py     # Handler TikTok Live events
├── requirements.txt
├── .env.example      # Template konfigurasi
├── tiktok-bot.service # Systemd service
└── README.md
```
