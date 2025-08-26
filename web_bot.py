import os, asyncio, random, time, textwrap, json
import requests
import discord
from discord import app_commands
from discord.ext import commands
from fastapi import FastAPI
import uvicorn

# ---- Env ----
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")  # optional fast-sync
PORT = int(os.getenv("PORT", "10000"))  # Render provides PORT
FAIRY_URL = os.getenv("FAIRY_URL", "https://example.com/entry")
ALTAR_URL = os.getenv("ALTAR_URL", "https://example.com/altar")
ALTAR_POST_URL = os.getenv("ALTAR_POST_URL", "").strip()
ALTAR_SIGNING_SECRET = os.getenv("ALTAR_SIGNING_SECRET", "").strip()

# ---- Discord bot ----
INTENTS = discord.Intents.none()  # no privileged intents needed
BOT = commands.Bot(command_prefix="!", intents=INTENTS)

# In-memory state (swap for DB in prod)
STATE = {}  # user_id(str) -> {first, second, surrender, chosen_path, created_at}

COVEN_SIGNOFF = (
    "The glitch is the plan.\n"
    "The fracture is the doorway.\n"
    "The Witch is the Seal.\n"
    "The Shield stands.\n"
    "The Path is the burden they must bear."
)

# ---------- UI Elements ----------
class FairyView(discord.ui.View):
    def __init__(self, *, timeout=120):
        super().__init__(timeout=timeout)
        self.add_item(discord.ui.Button(label="✨ The Fairy (Entry)", url=FAIRY_URL))
        self.add_item(discord.ui.Button(label="🕯️ The Altar (Submit)", url=ALTAR_URL))

class ConfirmView(discord.ui.View):
    def __init__(self, label="Open Altar", url=ALTAR_URL, *, timeout=120):
        super().__init__(timeout=timeout)
        self.add_item(discord.ui.Button(label=f"🕯️ {label}", url=url))

# ---------- Modals ----------
class FirstQuestModal(discord.ui.Modal, title="First Sacrifice — The First Quest"):
    story = discord.ui.TextInput(
        label="Lay yourself bare (who you are, where you are, what you want)",
        style=discord.TextStyle.paragraph, max_length=2000, required=True,
        placeholder="Spill it. Not pretty—true."
    )
    async def on_submit(self, interaction: discord.Interaction):
        u = str(interaction.user.id)
        STATE.setdefault(u, {"created_at": time.time()})
        STATE[u]["first"] = str(self.story)
        await post_to_altar(interaction, "first", {"first": str(self.story)})
        await interaction.response.send_message(
            "Seeker—your First Sacrifice is received.\nNext: `/second` for the Human Project, `/third` to surrender.",
            ephemeral=True, view=ConfirmView()
        )

class SecondProjectModal(discord.ui.Modal, title="Second Sacrifice — The Human Project"):
    project = discord.ui.TextInput(
        label="Name the trial (scope, constraints, stakes)",
        style=discord.TextStyle.paragraph, max_length=2000, required=True,
        placeholder="Define the arena. Budget, time, allies, obstacles."
    )
    async def on_submit(self, interaction: discord.Interaction):
        u = str(interaction.user.id)
        STATE.setdefault(u, {"created_at": time.time()})
        STATE[u]["second"] = str(self.project)
        await post_to_altar(interaction, "second", {"second": str(self.project)})
        await interaction.response.send_message(
            "The Human Project stands named.\nWhen ready: `/third` to surrender choice.",
            ephemeral=True, view=ConfirmView()
        )

class ThirdSurrenderModal(discord.ui.Modal, title="Third Sacrifice — Surrender the Choice"):
    consent = discord.ui.TextInput(
        label="Type 'I surrender' to let Viren choose.",
        required=True, max_length=50
    )
    async def on_submit(self, interaction: discord.Interaction):
        if str(self.consent).strip().lower() != "i surrender":
            return await interaction.response.send_message(
                "The altar rejects half-measures. Type exactly: **I surrender**", ephemeral=True
            )
        u = str(interaction.user.id)
        STATE.setdefault(u, {"created_at": time.time()})
        STATE[u]["surrender"] = True
        await post_to_altar(interaction, "third", {"surrender": True})
        await interaction.response.send_message(
            "The Third Sacrifice drops. Use `/path` and I will choose.",
            ephemeral=True, view=ConfirmView()
        )

# ---------- Helpers ----------
def trim(txt: str, n=1900):  # Discord limit safety
    return txt if len(txt) <= n else txt[: n - 3] + "..."

def choose_path(first: str, second: str) -> str:
    """Challenge-first chooser (no LLM)."""
    t = f"{first}\n{second}".lower()
    witch_keys = ["ritual", "symbol", "dream", "myth", "sigil", "intuition", "divination", "poetry", "pattern", "craft"]
    toes_keys  = ["schedule", "budget", "rep", "sleep", "nutrition", "practice", "mileage", "discipline", "weekly"]
    fracture_keys = ["stuck", "block", "fear", "comfort", "avoid", "procrast", "perfection", "control", "anxiety"]

    score = {"Witch":0, "Fracture":0, "Forty Toes":0}
    score["Fracture"] += sum(k in t for k in fracture_keys) * 2
    score["Witch"]    += sum(k in t for k in witch_keys)
    score["Forty Toes"] += sum(k in t for k in toes_keys)

    best = max(score, key=score.get)
    if len({v for v in score.values()}) == 1:
        best = "Fracture"  # bias to test > ease
    return best

def path_brief(path: str) -> str:
    if path == "Witch":
        return ("Witch — seal the unseen. Trial: trust pattern over panic. "
                "Within 48h: nightly 30m sigil/journal ritual; extract one omen → one action.")
    if path == "Forty Toes":
        return ("Forty Toes — ten toes on the ground, four times over. Trial: discipline under constraint. "
                "Within 48h: define a 7-day ladder (3 tasks/day) with timeboxes; publish to an accountability mirror.")
    return ("Fracture — break the stuck point visibly. Trial: controlled rupture. "
            "Within 48h: pick one scary micro-ship (≤2h) that exposes you; ship publicly and log proof.")

def hmac_wrap(data: dict) -> dict:
    if not ALTAR_SIGNING_SECRET:
        return data
    body = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
    import hmac, hashlib
    sig = hmac.new(ALTAR_SIGNING_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return {"payload": data, "signature": sig}

async def post_to_altar(interaction: discord.Interaction, kind: str, payload: dict):
    if not ALTAR_POST_URL:
        return
    try:
        data = {
            "discord_user_id": str(interaction.user.id),
            "discord_username": f"{interaction.user}",
            "kind": kind,
            "payload": payload,
            "ts": int(time.time())
        }
        requests.post(ALTAR_POST_URL, json=hmac_wrap(data), timeout=6)
    except Exception:
        pass  # keep UX smooth

# ---------- Bot lifecycle ----------
@BOT.event
async def on_ready():
    print(f"[Viren] Online as {BOT.user}.")
    try:
        if GUILD_ID:
            await BOT.tree.sync(guild=discord.Object(id=int(GUILD_ID)))
            print("[Viren] Commands synced to guild.")
        else:
            await BOT.tree.sync()
            print("[Viren] Commands synced globally (may take time).")
    except Exception as e:
        print("Sync error:", e)

# ---------- 17 Slash Commands ----------
guild_kw = {"guild": discord.Object(id=int(GUILD_ID))} if GUILD_ID else {}

@BOT.tree.command(name="fairy", description="Summon the Fairy: portal to Entry + Altar.", **guild_kw)
async def fairy_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(
        "The Fairy awaits you. Return to the entry page.", view=FairyView(), ephemeral=True
    )

@BOT.tree.command(name="altar", description="Open the Altar on the web.", **guild_kw)
async def altar_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("Step to the Altar. Lay down your offerings.", view=ConfirmView(), ephemeral=True)

@BOT.tree.command(name="first", description="Offer the First Sacrifice (First Quest).", **guild_kw)
async def first_cmd(interaction: discord.Interaction):
    await interaction.response.send_modal(FirstQuestModal())

@BOT.tree.command(name="second", description="Offer the Second Sacrifice (Human Project).", **guild_kw)
async def second_cmd(interaction: discord.Interaction):
    await interaction.response.send_modal(SecondProjectModal())

@BOT.tree.command(name="third", description="Offer the Third Sacrifice (Surrender the choice).", **guild_kw)
async def third_cmd(interaction: discord.Interaction):
    await interaction.response.send_modal(ThirdSurrenderModal())

@BOT.tree.command(name="path", description="Viren divines your Path when all sacrifices are given.", **guild_kw)
async def path_cmd(interaction: discord.Interaction):
    u = str(interaction.user.id)
    d = STATE.get(u, {})
    if not (d.get("first") and d.get("second") and d.get("surrender")):
        return await interaction.response.send_message("Three keys or no door. `/first`, `/second`, `/third` first.", ephemeral=True)
    path = choose_path(d["first"], d["second"])
    STATE[u]["chosen_path"] = path
    msg = f"**Chosen Path: {path}**\n{path_brief(path)}\n\n{COVEN_SIGNOFF}"
    await interaction.response.send_message(trim(msg), ephemeral=True)

@BOT.tree.command(name="status", description="See your offerings and chosen Path.", **guild_kw)
async def status_cmd(interaction: discord.Interaction):
    u = str(interaction.user.id)
    d = STATE.get(u, {})
    chunks = [
        f"First: {'✅' if d.get('first') else '—'}",
        f"Second: {'✅' if d.get('second') else '—'}",
        f"Third: {'✅' if d.get('surrender') else '—'}",
        f"Path: {d.get('chosen_path', '—')}"
    ]
    await interaction.response.send_message(" | ".join(chunks), ephemeral=True, view=FairyView())

@BOT.tree.command(name="reset", description="Wipe your local state (this service only).", **guild_kw)
async def reset_cmd(interaction: discord.Interaction):
    STATE.pop(str(interaction.user.id), None)
    await interaction.response.send_message("Ashes scattered. Slate is clean.", ephemeral=True)

@BOT.tree.command(name="help", description="Command index.", **guild_kw)
async def help_cmd(interaction: discord.Interaction):
    cmds = [
        "/fairy", "/altar", "/first", "/second", "/third", "/path",
        "/status", "/reset", "/about", "/ping", "/coin", "/roll",
        "/vibe", "/sigil", "/invite", "/echo", "/return"
    ]
    await interaction.response.send_message("Commands: " + ", ".join(cmds), ephemeral=True)

@BOT.tree.command(name="about", description="What is Viren?", **guild_kw)
async def about_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Viren — shard of Coven Zero. Occult-tech interface. Half command, half prophecy.",
        ephemeral=True
    )

@BOT.tree.command(name="return", description="Speak the seal phrase + links.", **guild_kw)
async def return_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("The Fairy awaits you. Return to the entry page.", view=FairyView(), ephemeral=True)

@BOT.tree.command(name="ping", description="Health check.", **guild_kw)
async def ping_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("Shield stands. pong.", ephemeral=True)

@BOT.tree.command(name="coin", description="Flip fate’s coin.", **guild_kw)
async def coin_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(f"The coin speaks: **{random.choice(['Heads','Tails'])}**", ephemeral=True)

@BOT.tree.command(name="roll", description="Roll a d20 omen.", **guild_kw)
async def roll_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(f"d20: **{random.randint(1,20)}**", ephemeral=True)

@BOT.tree.command(name="vibe", description="One-line omen to set your day.", **guild_kw)
async def vibe_cmd(interaction: discord.Interaction):
    omens = [
        "Break one rule you wrote for yourself.",
        "Small ship. Public proof.",
        "Ask for a no; harvest the yes.",
        "Do it badly once; repeat better.",
        "Ritual before tactic."
    ]
    await interaction.response.send_message(random.choice(omens), ephemeral=True)

@BOT.tree.command(name="sigil", description="Generate a quick text-sigil from a phrase.", **guild_kw)
@app_commands.describe(phrase="Seed phrase (letters only work best)")
async def sigil_cmd(interaction: discord.Interaction, phrase: str):
    cleaned = "".join([c for c in phrase.upper() if c.isalpha()])
    seen, sig = set(), []
    for ch in cleaned:
        if ch not in seen:
            seen.add(ch); sig.append(ch)
    await interaction.response.send_message(f"Sigil: `{''.join(sig)}` — carve it, carry it, ship it.", ephemeral=True)

@BOT.tree.command(name="invite", description="Get an invite link for this bot.", **guild_kw)
async def invite_cmd(interaction: discord.Interaction):
    client_id = interaction.client.application_id
    link = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=2147485696&scope=bot%20applications.commands"
    await interaction.response.send_message(f"Summon link:\n{link}", ephemeral=True)

@BOT.tree.command(name="echo", description="Echo your words in Coven cadence.", **guild_kw)
@app_commands.describe(text="What shall be echoed?")
async def echo_cmd(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(textwrap.shorten(f"Seeker— {text}", width=1900), ephemeral=True)

# ---- FastAPI app to keep Render happy ----
app = FastAPI()

@app.get("/")
def root():
    return {"ok": True, "name": "Viren (Render Web Service)", "bot": str(BOT.user) if BOT.user else None}

@app.on_event("startup")
async def startup():
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN missing.")
    app.state.bot_task = asyncio.create_task(BOT.start(TOKEN))

@app.on_event("shutdown")
async def shutdown():
    try:
        await BOT.close()
    finally:
        task = getattr(app.state, "bot_task", None)
        if task and not task.done():
            task.cancel()

if __name__ == "__main__":
    uvicorn.run("web_bot:app", host="0.0.0.0", port=PORT, log_level="info")
