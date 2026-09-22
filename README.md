# Vinod-Ji Device DB Bot

Telegram bot jisme tum **apna device database** daalte ho — `/find` karte hi **device aa jati hai**.

## Features

- SQLite DB (har user ki apni devices alag)
- `/add` se device add
- CSV / JSON file chat mein bhej ke **poori DB import**
- `/find` se naam, model, serial, IMEI, phone search
- Telegram ke bina local CLI se bhi test

## Setup (Telegram)

1. Telegram pe [@BotFather](https://t.me/BotFather) kholo → `/newbot` → token copy karo
2. Repo clone / download karke:

```bash
cd Vinod-Ji-2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

3. `.env` mein token daalo:

```env
TELEGRAM_BOT_TOKEN=123456:AA...your_real_token
DATABASE_PATH=data/devices.db
```

4. Bot chalao:

```bash
python -m bot.main
```

5. Telegram pe apne bot ko open karo → `/start` → `/sample` → `/find iPhone`

## DB kaise daalo

### Option A — CSV file
Chat mein `devices.csv` bhej do. Columns:

```text
name,model,serial,imei,phone,notes
```

Sample: `sample_data/devices.csv`

### Option B — JSON file
Chat mein JSON bhejo. Sample: `sample_data/devices.json`

### Option C — command

```text
/add iPhone 14 | Apple | SN123 | 356789012345678 | 9876543210 | Ghar wala
```

## Commands

| Command | Kaam |
|---------|------|
| `/start` `/help` | Help |
| `/a deviceid` | ID / serial / IMEI se device lao |
| `/add ...` | Device add |
| `/list` | Saari devices |
| `/find query` | Search — device aa jayegi |
| `/count` | Kitni devices |
| `/del id` | Delete |
| `/clear` | Apni DB wipe |
| `/sample` | Demo data load |
| CSV/JSON file | Bulk import |

## Local CLI (bina Telegram)

```bash
python -m bot.cli import sample_data/devices.csv
python -m bot.cli list
python -m bot.cli a 1
python -m bot.cli find iPhone
python -m bot.cli add "My Phone" --model Android --imei 123
```

## Privacy note

Har Telegram chat ki devices alag `owner_chat_id` se store hoti hain. Sirf apna data daalo — dusre logon ka private data import mat karo.
