import "dotenv/config";
import { REST, Routes, SlashCommandBuilder } from "discord.js";

const { DISCORD_TOKEN, CLIENT_ID, GUILD_ID } = process.env;
if (!DISCORD_TOKEN || !CLIENT_ID || !GUILD_ID) {
  console.error("Missing DISCORD_TOKEN / CLIENT_ID / GUILD_ID");
  process.exit(1);
}

const b = (name, desc) => new SlashCommandBuilder().setName(name).setDescription(desc);

// 15 Coven-style commands
const commands = [
  b("welcome", "Summon the Welcome Fairy with the entry gate."),
  b("fairy", "Call the Fairy to your side."),
  b("gate", "Reveal the Entry Gate URL."),
  new SlashCommandBuilder()
    .setName("seal")
    .setDescription("Name your daemon; bind the seal.")
    .addStringOption(o => o.setName("name").setDescription("Daemon name").setRequired(true)),
  b("altar", "Approach the Altar; receive instructions."),
  b("relic", "Offer a relic; the altar will flare."),
  b("quest", "See the three sacrifices/quests."),
  new SlashCommandBuilder()
    .setName("proof")
    .setDescription("Offer proof of your sacrifice (URL or short note).")
    .addStringOption(o => o.setName("note").setDescription("URL or short note").setRequired(false)),
  b("path", "Let the daemon describe the Paths."),
  b("witchpath", "Speak the Witch Path."),
  b("fracturepath", "Speak the Fracture Path."),
  b("fortypath", "Speak the Path of Forty Toes."),
  b("summon", "Heartbeat check — awaken and respond."),
  b("bless", "Receive a blessing for the road."),
  b("purge", "Cleanse your intent; begin again.")
].map(c => c.toJSON());

const rest = new REST({ version: "10" }).setToken(DISCORD_TOKEN);

(async () => {
  try {
    console.log("Registering guild commands…");
    await rest.put(Routes.applicationGuildCommands(CLIENT_ID, GUILD_ID), { body: commands });
    console.log("Slash commands registered.");
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
})();
