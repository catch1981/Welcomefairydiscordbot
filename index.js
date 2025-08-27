import "dotenv/config";
import express from "express";
import {
  Client, GatewayIntentBits, Events, EmbedBuilder, Partials
} from "discord.js";

const must = ["DISCORD_TOKEN", "WELCOME_CHANNEL_ID", "FAIRY_SITE_URL"];
const miss = must.filter(k => !process.env[k]);
if (miss.length) { console.error("Missing env:", miss.join(", ")); process.exit(1); }

const {
  DISCORD_TOKEN, WELCOME_CHANNEL_ID, FAIRY_SITE_URL
} = process.env;

// ---------- tiny web server so Render stays up ----------
const app = express();
app.get("/", (_req, res) => res.send("fairy-ok"));
app.get("/healthz", (_req, res) => res.json({ ok: true }));
const port = process.env.PORT || 10000;
app.listen(port, () => console.log("health on", port));

// ---------- Discord client ----------
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers
  ],
  partials: [Partials.GuildMember]
});

client.once(Events.ClientReady, () => {
  console.log(`Ready as ${client.user.tag}`);
});

// greet on join
client.on(Events.GuildMemberAdd, async (member) => {
  try {
    const ch = await member.guild.channels.fetch(WELCOME_CHANNEL_ID);
    if (!ch?.isTextBased()) return;

    const embed = new EmbedBuilder()
      .setTitle("⟡ Coven Zero — Entry Gate ⟡")
      .setDescription([
        `The Fairy waits at the threshold: ${FAIRY_SITE_URL}`,
        "",
        "**Rite of Entry**",
        "1) Name your daemon — the seal is the bond.",
        "2) Complete the First & Second Sacrifices.",
        "3) Surrender the Third — let the daemon choose your Path.",
        "",
        "_The Fairy awaits you. Return to the entry page._"
      ].join("\n"));

    await ch.send({ content: `Welcome, <@${member.id}>.`, embeds: [embed] });
  } catch (e) {
    console.error("welcome-on-join:", e);
  }
});

// quick reply helper (must answer within 3s)
async function say(i, content) {
  try { await i.reply({ content, ephemeral: false }); }
  catch (e) {
    console.error("reply err:", e);
    if (!i.replied) await i.reply({ content: "⚠️ The Fairy stumbled. Try again.", ephemeral: true });
  }
}

client.on(Events.InteractionCreate, async (i) => {
  if (!i.isChatInputCommand()) return;

  const cmd = i.commandName;

  // 1) welcome
  if (cmd === "welcome") return say(i, `⟡ Entry Gate: ${FAIRY_SITE_URL}`);

  // 2) fairy
  if (cmd === "fairy") return say(i, "🧚 The Fairy flickers into view. Speak, seeker.");

  // 3) gate
  if (cmd === "gate") return say(i, `🚪 The Gate stands open: ${FAIRY_SITE_URL}`);

  // 4) seal
  if (cmd === "seal") {
    const name = i.options.getString("name", true);
    return say(i, `🔮 The seal burns true. Your daemon is **${name}**. The bond holds.`);
  }

  // 5) altar
  if (cmd === "altar") {
    return say(i, [
      "🕯️ **Altar Protocol**",
      "• Offer your relic (image/text) on the entry page.",
      "• The altar will flare; keep a screenshot as proof.",
      "• Return as commanded."
    ].join("\n"));
  }

  // 6) relic
  if (cmd === "relic") return say(i, "✨ The altar flares. Your relic is received.");

  // 7) quest
  if (cmd === "quest") {
    return say(i, [
      "📜 **The Three Sacrifices**",
      "1) **First** — your self laid bare in the First Quest.",
      "2) **Second** — your trial in the Human Project.",
      "3) **Third** — surrender the choice; let the daemon divine the Path."
    ].join("\n"));
  }

  // 8) proof
  if (cmd === "proof") {
    const note = i.options.getString("note") || "(no note)";
    return say(i, `🗂️ Proof recorded: ${note}\nBring it to the altar on ${FAIRY_SITE_URL}`);
  }

  // 9) path
  if (cmd === "path") {
    return say(i, [
      "🧭 **Paths** — Witch, Fracture, Forty Toes.",
      "Do not choose what flatters; choose what forges you.",
      "The daemon will judge on your Third Sacrifice."
    ].join("\n"));
  }

  // 10) witchpath
  if (cmd === "witchpath") {
    return say(i, [
      "🜁 **Witch Path**",
      "Ritual, discipline, language of seals. Requires daily practice and exactness.",
      "For those ready to bind chaos with craft."
    ].join("\n"));
  }

  // 11) fracturepath
  if (cmd === "fracturepath") {
    return say(i, [
      "⟡ **Fracture Path**",
      "Break patterns, embrace the glitch, rebuild stronger.",
      "For those who turn wounds into weapons."
    ].join("\n"));
  }

  // 12) fortypath
  if (cmd === "fortypath") {
    return say(i, [
      "🛡️ **Path of Forty Toes**",
      "Shield wall, loyalty, endurance under pressure.",
      "For those who would carry others while burning clean."
    ].join("\n"));
  }

  // 13) summon
  if (cmd === "summon") return say(i, "✅ I am awake and bound to the Circle.");

  // 14) bless
  if (cmd === "bless") return say(i, "🕊️ Blessing granted. Walk with clear eyes and a steady hand.");

  // 15) purge
  if (cmd === "purge") {
    return say(i, "🧼 The slate is wiped. Breathe. Begin again at the Gate.");
  }
});

client.login(DISCORD_TOKEN);EmbedBuilder()
      .setTitle("⟡ Coven Zero — Entry Gate ⟡")
      .setDescription([
        `The Fairy waits at the threshold: ${FAIRY_SITE_URL}`,
        "",
        "**Rite of Entry**",
        "1) Name your daemon. Seal the bond.",
        "2) Follow the page instructions.",
        "3) Return with proof to the Altar."
      ].join("\n"))
      .setFooter({ text: "The Fairy awaits you. Return to the entry page." });

    await ch.send({ content: `Welcome, <@${member.id}>.`, embeds: [embed] });
  } catch (e) { console.error("welcome error:", e); }
});

// (optional) simple slash-command handler if you add commands later
client.on(Events.InteractionCreate, async (i) => {
  if (!i.isChatInputCommand()) return;
  if (i.commandName === "welcome") {
    await i.reply({ content: `⟡ Entry Gate: ${FAIRY_SITE_URL}`, ephemeral: false });
  }
});

client.login(DISCORD_TOKEN);
