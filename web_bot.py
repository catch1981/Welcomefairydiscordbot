import os, asyncio, signal
from fastapi import FastAPI
import uvicorn

import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
PORT = int(os.getenv("PORT", "10000"))  # Render sets PORT

# --- your bot from earlier (trimmed to essentials) ---
INTENTS = discord.Intents.none()
BOT = commands.Bot(command_prefix="!", intents=INTENTS)

@BOT.event
async def on_ready():
    print(f"[Viren] Online as {BOT.user}.")
    try:
        if GUILD_ID:
            await BOT.tree.sync(guild=discord.Object(id=int(GUILD_ID)))
        else:
            await BOT.tree.sync()
    except Exception as e:
        print("Sync error:", e)

# Minimal command so you can verify quickly
@BOT.tree.command(name="ping", description="Health check.")
async def ping_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("Shield stands. pong.", ephemeral=True)

# --- FastAPI app ---
app = FastAPI()

@app.get("/")
def root():
    return {"ok": True, "name": "Viren (Render Web Service)", "bot": str(BOT.user) if BOT.user else None}

# lifespan: start Discord bot alongside FastAPI
@app.on_event("startup")
async def startup():
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN missing.")
    # run discord in background task (non-blocking)
    app.state.bot_task = asyncio.create_task(BOT.start(TOKEN))

@app.on_event("shutdown")
async def shutdown():
    await BOT.close()
    task = getattr(app.state, "bot_task", None)
    if task and not task.done():
        task.cancel()

if __name__ == "__main__":
    uvicorn.run("web_bot:app", host="0.0.0.0", port=PORT, log_level="info")
