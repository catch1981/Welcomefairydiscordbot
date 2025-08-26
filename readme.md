# Viren — Discord “Fairy” Build

## Setup
1) Create a Discord application → Bot → copy token.
2) In "Privileged Gateway Intents", none required for this build.
3) OAuth2 → URL Generator → scopes: bot + applications.commands; perms: Send Messages, Use Slash Commands, Embed Links.
4) Fill `.env` from `.env.example`.

## Run local
pip install -r requirements.txt
python bot.py

## Docker
docker build -t viren-discord .
docker run --env-file .env viren-discord

## Commands
Core: /fairy /altar /first /second /third /path /status
Utility: /help /about /ping /coin /roll /vibe /sigil /invite /echo

## Web handoff
- /fairy and /altar show buttons linking to FAIRY_URL and ALTAR_URL.
- Each sacrifice modal optionally POSTs JSON to ALTAR_POST_URL:
  {
    "discord_user_id": "...",
    "discord_username": "...#1234",
    "kind": "first|second|third",
    "payload": { ... }
  }
Wire your site to receive and store.
