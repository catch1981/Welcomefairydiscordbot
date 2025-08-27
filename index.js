import "dotenv/config";
import express from "express";
import { Client, GatewayIntentBits, Events, EmbedBuilder } from "discord.js";

const must = ["DISCORD_TOKEN","WELCOME_CHANNEL_ID","FAIRY_SITE_URL"];
const miss = must.filter(k => !process.env[k]);
if (miss.length) { console.error("Missing env:", miss.join(", ")); process.exit(1); }

const { DISCORD_TOKEN, WELCOME_CHANNEL_ID, FAIRY_SITE_URL } = process.env;

const app = express();
app.get("/", (_req,res)=>res.send("fairy-ok"));
app.get("/healthz", (_req,res)=>res.json({ok:true}));
const port = process.env.PORT || 10000;
app.listen(port, ()=>console.log("health on", port));

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers]
});

client.once(Events.ClientReady, () => console.log(`Ready as ${client.user.tag}`));

client.on(Events.GuildMemberAdd, async (member) => {
  try {
    const ch = await member.guild.channels.fetch(process.env.WELCOME_CHANNEL_ID);
    if (!ch?.isTextBased()) return;

    const embed = new EmbedBuilder()
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
