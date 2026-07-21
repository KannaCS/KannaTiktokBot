# Setup Guide — KannaTiktokBot

Panduan lengkap setup bot dari nol di Ubuntu server.

---

## Prasyarat

- Ubuntu server (fresh atau existing)
- Python 3.8+
- Akses root atau sudo
- Groq API key → https://console.groq.com/keys
- Akun TikTok yang sedang live

---

## 1. Install Dependencies Sistem

```bash
apt update
apt install -y python3 python3-pip python3-venv git
```

---

## 2. Clone Repository

```bash
git clone https://github.com/KannaCS/KannaTiktokBot
cd KannaTiktokBot
```

---

## 3. Buat Virtual Environment & Install Package

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Install Playwright browser (wajib — dilakukan sekali saja)

```bash
playwright install chromium
playwright install-deps chromium   # install OS-level deps (Linux)
```

---

## 4. Buat File .env

Jalankan perintah berikut (ganti nilai yang sesuai):

```bash
cat > .env << 'EOF'
TIKTOK_USERNAME=KannaCSX
TIKTOK_SESSION_ID=GANTI_DENGAN_SESSION_ID_KAMU
GROQ_API_KEY=gsk_GANTI_DENGAN_API_KEY_KAMU
BOT_PERSONA_NAME=Andi
BOT_LANGUAGE=id
COMMENT_MIN_INTERVAL=30
COMMENT_MAX_INTERVAL=90
REPLY_TO_COMMENTS=true
MAX_REPLIES_PER_MINUTE=2
PLAYWRIGHT_HEADLESS=true
EOF
```

### Cara ambil TIKTOK_SESSION_ID

1. Login TikTok di browser (Chrome/Firefox)
2. Buka DevTools → **F12**
3. Tab **Application** → **Cookies** → `https://www.tiktok.com`
4. Cari cookie bernama `sessionid` dan copy nilainya

> **Catatan:** Dapatkan Groq API key baru di https://console.groq.com/keys

Verifikasi isi `.env`:
```bash
cat .env
```

---

## 5. Test Jalankan Bot

```bash
source venv/bin/activate
python main.py
```

Bot akan connect ke live `@KannaCSX`. Pastikan akun TikTok tersebut sedang live saat menjalankan bot.

Untuk stop: tekan `Ctrl+C`

---

## 6. Deploy Pakai Systemd (Jalan Terus di Background)

### Edit service file

Buka `tiktok-bot.service` dan pastikan path-nya benar:

```bash
cat tiktok-bot.service
```

Ubah isi service file agar sesuai dengan path di server kamu:

```ini
[Unit]
Description=TikTok Live Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/KannaTiktokBot
ExecStart=/root/KannaTiktokBot/venv/bin/python main.py
Restart=on-failure
RestartSec=10
EnvironmentFile=/root/KannaTiktokBot/.env

[Install]
WantedBy=multi-user.target
```

### Aktifkan service

```bash
cp tiktok-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable tiktok-bot
systemctl start tiktok-bot
```

### Cek status

```bash
systemctl status tiktok-bot
```

### Lihat log real-time

```bash
journalctl -u tiktok-bot -f
```

---

## 7. Update Bot (Kalau Ada Perubahan)

```bash
cd /root/KannaTiktokBot
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart tiktok-bot
```

---

## Perintah Berguna

| Perintah | Fungsi |
|---|---|
| `systemctl start tiktok-bot` | Jalankan bot |
| `systemctl stop tiktok-bot` | Hentikan bot |
| `systemctl restart tiktok-bot` | Restart bot |
| `systemctl status tiktok-bot` | Cek status |
| `journalctl -u tiktok-bot -f` | Lihat log live |
| `tail -f /root/KannaTiktokBot/bot.log` | Lihat log file |

---

## Troubleshooting

**`No matching distribution found for TikTokLive`**
```bash
pip install TikTokLive==6.4.5.post1
```

**Edit file di server**  
Bisa pakai `nano .env` untuk edit file secara interaktif.

**Bot tidak connect ke live**  
Pastikan akun TikTok sedang live saat bot dijalankan.

**`ModuleNotFoundError`**  
Pastikan virtual environment aktif:
```bash
source venv/bin/activate
```

**Komentar tidak terkirim / chat input tidak ditemukan**  
TikTok kadang mengubah selector HTML-nya. Buka bot dengan `PLAYWRIGHT_HEADLESS=false`,
lihat elemen chat input, lalu update `CHAT_INPUT_SELECTOR` dan `SEND_BUTTON_SELECTOR`
di `tiktok_poster.py` sesuai yang ada di halaman.

**Playwright tidak bisa launch di server (missing libs)**  
```bash
playwright install-deps chromium
```

**Debug — lihat apa yang dilakukan browser**  
Set `PLAYWRIGHT_HEADLESS=false` di `.env`. Browser Chromium akan terbuka secara
visible sehingga kamu bisa lihat prosesnya secara langsung.
