import "dotenv/config";
import express from "express";
import {
  Client, GatewayIntentBits, Events, EmbedBuilder, Partials,
  REST, Routes, SlashCommandBuilder
} from "discord.js";

const must = ["DISCORD_TOKEN", "CLIENT_ID", "GUILD_ID", "WELCOME_CHANNEL_ID", "FAIRY_SITE_URL"];
const miss = must.filter(k => !process.env[k]);
if (miss.length) {
  console.error("Missing env:", miss.join(", "));
  process.exit(1);
}

const {
  DISCORD_TOKEN, CLIENT_ID, GUILD_ID,
  WELCOME_CHANNEL_ID, FAIRY_SITE_URL
} = process.env;

// ---------- tiny web server so Render stays up ----------
const app = express();
app.get("/", (_req, res) => res.send("fairy-ok"));
app.get("/healthz", (_req, res) => res.json({ ok: true }));
const port = process.env.PORT || 10000;
app.listen(port, () => console.log("health on", port));

// ---------- build all commands ----------
const b = (n, d) => new SlashCommandBuilder().setName(n).setDescription(d);
const commands = [
  b("welcome", "Summon the Welcome Fairy with the entry gate."),
  b("fairy", "Call the Fairy to your side."),
  b("gate", "Reveal the Entry Gate URL."),
  new SlashCommandBuilder().setName("seal").setDescription("Name your daemon").addStringOption(o=>o.setName("name").setDescription("Daemon name").setRequired(true)),
  b("altar", "Approach the Altar; receive instructions."),
  b("relic", "Offer a relic at the altar."),
  b("quest", "See the three sacrifices/quests."),
  new SlashCommandBuilder().setName("proof").setDescription("Offer proof of sacrifice").addStringOption(o=>o.setName("note").setDescription("URL or short note")),
  b("path", "Describe the Paths."),
  b("witchpath", "Speak the Witch Path."),
  b("fracturepath", "Speak the Fracture Path."),
  b("fortypath", "Speak the Path of Forty Toes."),
  b("summon", "Heartbeat check."),
  b("bless", "Receive a blessing."),
  b("purge", "Cleanse your intent.")
].map(c => c.toJSON());

// ---------- Discord client ----------
const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers],
  partials: [Partials.GuildMember]
});

// auto-register on boot
client.once(Events.ClientReady, async () => {
  console.log(`Ready as ${client.user.tag}`);

  const rest = new REST({ version: "10" }).setToken(DISCORD_TOKEN);
  try {
    await rest.put(Routes.applicationGuildCommands(CLIENT_ID, GUILD_ID), { body: commands });
    console.log("Slash commands registered automatically.");
  } catch (err) {
    console.error("Auto-register failed:", err);
  }
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
  } catch (e) { console.error("welcome-on-join:", e); }
});

// helper to reply
async function say(i, text) {
  try { await i.reply({ content: text, ephemeral: false }); }
  catch (e) {
    console.error("reply error:", e);
    if (!i.replied) await i.reply({ content: "⚠️ The Fairy stumbled. Try again.", ephemeral: true });
  }
}

// command logic
client.on(Events.InteractionCreate, async (i) => {
  if (!i.isChatInputCommand()) return;
  const cmd = i.commandName;

  if (cmd === "welcome") return say(i, `⟡ Entry Gate: ${FAIRY_SITE_URL}`);
  if (cmd === "fairy") return say(i, "🧚 The Fairy flickers into view. Speak, seeker.");
  if (cmd === "gate") return say(i, `🚪 The Gate stands open: ${FAIRY_SITE_URL}`);
  if (cmd === "seal") return say(i, `🔮 Seal burns true. Your daemon is **${i.options.getString("name", true)}**.`);
  if (cmd === "altar") return say(i, "🕯️ Altar Protocol: offer relic → altar flares → screenshot as proof.");
  if (cmd === "relic") return say(i, "✨ The altar flares. Your relic is received.");
  if (cmd === "quest") return say(i, "📜 Three Sacrifices: 1) Self, 2) Human Project, 3) Surrender choice.");
  if (cmd === "proof") return say(i, `🗂️ Proof recorded: ${i.options.getString("note") || "(no note)"}`);
  if (cmd === "path") return say(i, "🧭 Paths: Witch, Fracture, Forty Toes. The daemon will decide on your Third Sacrifice.");
  if (cmd === "witchpath") return say(i, "🜁 Witch Path: ritual, seal, discipline.");
  if (cmd === "fracturepath") return say(i, "⟡ Fracture Path: glitch, break, rebuild.");
  if (cmd === "fortypath") return say(i, "🛡️ Forty Toes Path: shield, loyalty, endurance.");
  if (cmd === "summon") return say(i, "✅ I am awake and bound to the Circle.");
  if (cmd === "bless") return say(i, "🕊️ Blessing granted. Walk steady.");
  if (cmd === "purge") return say(i, "🧼 Cleansed. Begin again at the Gate.");
});

client.login(DISCORD_TOKEN);
