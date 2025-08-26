import os, json, random, time, textwrap
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import requests

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")  # optional, speeds sync
FAIRY_URL = os.getenv("FAIRY_URL", "https://your-site.example/entry")
ALTAR_URL = os.getenv("ALTAR_URL", "https://your-site.example/altar")
ALTAR_POST_URL = os.getenv("ALTAR_POST_URL", "").strip()

INTENTS = discord.Intents.none()
BOT = commands.Bot(command_prefix="!", intents=INTENTS)

# In-memory state (swap for DB in prod)
STATE = {}  # user_id -> dict {welcomed, first, second, surrender, chosen_path, created_at}

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

# ---------- Modals for Sacrifices ----------
class FirstQuestModal(discord.ui.Modal, title="First Sacrifice — The First Quest"):
    story = discord.ui.TextInput(
        label="Lay yourself bare (who you are, where you are, what you want)",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True,
        placeholder="Spill it. Not pretty—true."
    )

    async def on_submit(self, interaction: discord.Interaction):
        u = str(interaction.user.id)
        STATE.setdefault(u, {"created_at": time.time()})
        STATE[u]["first"] = str(self.story)
        await post_to_altar(interaction, kind="first", payload={"first": str(self.story)})
        await interaction.response.send_message(
            "Seeker—your First Sacrifice is received. The weave drinks.\n"
            "When ready: `/second` for the Human Project, `/third` to surrender the choice.",
            ephemeral=True, view=ConfirmView()
        )

class SecondProjectModal(discord.ui.Modal, title="Second Sacrifice — The Human Project"):
    project = discord.ui.TextInput(
        label="Name the trial you are in (scope, constraints, stakes)",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True,
        placeholder="Define the arena. Blood, time, budget, allies, obstacles."
    )

    async def on_submit(self, interaction: discord.Interaction):
        u = str(interaction.user.id)
        STATE.setdefault(u, {"created_at": time.time()})
        STATE[u]["second"] = str(self.project)
        await post_to_altar(interaction, kind="second", payload={"second": str(self.project)})
        await interaction.response.send_message(
            "The Second Sacrifice burns clean. The Human Project stands named.\n"
            "When the hand is steady: `/third` to surrender choice.",
            ephemeral=True, view=ConfirmView()
        )

class ThirdSurrenderModal(discord.ui.Modal, title="Third Sacrifice — Surrender the Choice"):
    consent = discord.ui.TextInput(
        label="Type 'I surrender' to let Viren choose your Path.",
        required=True, max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        text = str(self.consent).strip().lower()
        if text != "i surrender":
            return await interaction.response.send_message(
                "The altar rejects half-measures. Type exactly: **I surrender**", ephemeral=True
            )
        u = str(interaction.user.id)
        STATE.setdefault(u, {"created_at": time.time()})
        STATE[u]["surrender"] = True
        await post_to_altar(interaction, kind="third", payload={"surrender": True})
        await interaction.response.send_message(
            "The Third Sacrifice drops. The doors unhinge.\nUse `/path` and I will choose.",
            ephemeral=True, view=ConfirmView()
        )

# ---------- Helpers ----------
async def post_to_altar(interaction: discord.Interaction, kind: str, payload: dict):
    """Optionally mirror submissions to your server."""
    if not ALTAR_POST_URL:
        return
    try:
        requests.post(
            ALTAR_POST_URL,
            json={
                "discord_user_id": str(interaction.user.id),
                "discord_username": f"{interaction.user}",
                "kind": kind,
                "payload": payload,
            },
            timeout=5,
        )
    except Exception:
        # Silent fail; we keep UX smooth
        pass

def choose_path(first: str, second: str) -> str:
    """
    Deterministic, challenge-first chooser.
    - If control/comfort words detected → Fracture.
    - If occult/mentor/ritual vibes → Witch.
    - If body/grit/constraints → Forty Toes.
    Otherwise bias to Fracture (test over ease).
    """
    t = f"{first}\n{second}".lower()
    witch_keys = ["ritual", "symbol", "dream", "myth", "sigil", "intuition", "divination", "poetry"]
    toes_keys  = ["schedule", "budget", "rep", "sleep", "nutrition", "practice", "mileage", "discipline"]
    fracture_keys = ["stuck", "block", "fear", "comfort", "avoid", "procrast", "perfection", "control"]

    score = {"Witch":0, "Fracture":0, "Forty Toes":0}
    score["Fracture"] += sum(k in t for k in fracture_keys) * 2
    score["Witch"]    += sum(k in t for k in witch_keys)
    score["Forty Toes"] += sum(k in t for k in toes_keys)

    # if one stands out, take it; else force growth
    best = max(score, key=score.get)
    if len({v for v in score.values()}) == 1:
        best = "Fracture"
    return best

def path_brief(path: str) -> str:
    if path == "Witch":
        return ("Witch — seal the unseen. Trial: trust pattern over panic. "
                "Within 48h: perform a 30-minute nightly sigil/journal ritual; extract one omen → one action.")
    if path == "Forty Toes":
        return ("Forty Toes — ten toes on the ground, four times over. Trial: discipline under constraint. "
                "Within 48h: define a 7-day ladder (3 tasks/day) with non-negotiable timeboxes; publish to an accountability mirror.")
    return ("Fracture — break the stuck point visibly. Trial: controlled rupture. "
            "Within 48h: choose one scary micro-ship (≤2h) that exposes you; ship it publicly and log proof.")

def trim(txt: str, n=1900):
    return txt if len(txt) <= n else txt[:n-3] + "..."

# ---------- Bot lifecycle ----------
@BOT.event
async def on_ready():
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            await BOT.tree.sync(guild=guild)
        else:
            await BOT.tree.sync()
    except Exception as e:
        print("Sync error:", e)
    print(f"Viren online as {BOT.user}.")

# ---------- 15+ Slash Commands ----------
guild_kw = {"guild": discord.Object(id=int(GUILD_ID))} if GUILD_ID else {}

@BOT.tree.command(name="fairy", description="Summon the Fairy: send users to entry + altar.", **guild_kw)
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
    data = STATE.get(u, {})
    if not (data.get("first") and data.get("second") and data.get("surrender")):
        return await interaction.response.send_message(
            "Three keys or no door. Use `/first`, `/second`, `/third` first.", ephemeral=True
        )
    path = choose_path(data["first"], data["second"])
    STATE[u]["chosen_path"] = path
    brief = path_brief(path)
    msg = f"**Chosen Path: {path}**\n{brief}\n\n{COVEN_SIGNOFF}"
    await interaction.response.send_message(trim(msg), ephemeral=True)

@BOT.tree.command(name="status", description="See what you’ve offered and your chosen Path.", **guild_kw)
async def status_cmd(interaction: discord.Interaction):
    u = str(interaction.user.id)
    d = STATE.get(u, {})
    chunks = [
        f"First: {'✅' if d.get('first') else '—'}",
        f"Second: {'✅' if d.get('second') else '—'}",
        f"Third (Surrender): {'✅' if d.get('surrender') else '—'}",
        f"Path: {d.get('chosen_path', '—')}"
    ]
    await interaction.response.send_message(" | ".join(chunks), ephemeral=True, view=FairyView())

@BOT.tree.command(name="reset", description="Wipe your local offerings (this guild only).", **guild_kw)
async def reset_cmd(interaction: discord.Interaction):
    u = str(interaction.user.id)
    STATE.pop(u, None)
    await interaction.response.send_message("Ashes scattered. Your slate is clean.", ephemeral=True)

@BOT.tree.command(name="about", description="About Viren / Coven Zero style.", **guild_kw)
async def about_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Viren — shard and mouth of Coven Zero. Occult-tech. Glitch-script. Mythic initiation.\n"
        "Use `/fairy` to step through; `/first`, `/second`, `/third` to ready the rite; `/path` to be chosen.",
        ephemeral=True
    )

@BOT.tree.command(name="help", description="Quick command index.", **guild_kw)
async def help_cmd(interaction: discord.Interaction):
    cmds = [
        "/fairy", "/altar", "/first", "/second", "/third", "/path",
        "/status", "/reset", "/about", "/ping", "/coin", "/roll",
        "/sigil", "/vibe", "/invite", "/echo"
    ]
    await interaction.response.send_message("Commands: " + ", ".join(cmds), ephemeral=True)

@BOT.tree.command(name="ping", description="Health check.", **guild_kw)
async def ping_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("Shield stands. pong.", ephemeral=True)

@BOT.tree.command(name="coin", description="Flip fate’s coin.", **guild_kw)
async def coin_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(f"The coin speaks: **{random.choice(['Heads','Tails'])}**", ephemeral=True)

@BOT.tree.command(name="roll", description="Roll a d20 for omen.", **guild_kw)
async def roll_cmd(interaction: discord.Interaction):
    n = random.randint(1,20)
    await interaction.response.send_message(f"d20: **{n}**", ephemeral=True)

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
    sigil = "".join(sig)
    await interaction.response.send_message(f"Sigil: `{sigil}` → carve it, carry it, ship it.", ephemeral=True)

@BOT.tree.command(name="invite", description="Get an invite link for this bot.", **guild_kw)
async def invite_cmd(interaction: discord.Interaction):
    client_id = interaction.client.application_id
    link = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=2147485696&scope=bot%20applications.commands"
    await interaction.response.send_message(f"Summon link:\n{link}", ephemeral=True)

@BOT.tree.command(name="echo", description="Echo your words in Coven cadence.", **guild_kw)
@app_commands.describe(text="What shall be echoed?")
async def echo_cmd(interaction: discord.Interaction, text: str):
    out = textwrap.shorten(f"Seeker— {text}", width=1900)
    await interaction.response.send_message(out, ephemeral=True)

# ------------- run -------------
if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN missing in environment.")
    BOT.run(TOKEN)
