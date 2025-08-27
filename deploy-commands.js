import "dotenv/config";
import { REST, Routes, SlashCommandBuilder } from "discord.js";

const { DISCORD_TOKEN, CLIENT_ID, GUILD_ID } = process.env;
if (!DISCORD_TOKEN || !CLIENT_ID || !GUILD_ID) {
  console.error("Missing DISCORD_TOKEN / CLIENT_ID / GUILD_ID"); process.exit(1);
}

const welcome = new SlashCommandBuilder()
  .setName("welcome")
  .setDescription("Summon the Welcome Fairy.")
  .toJSON();

const rest = new REST({ version: "10" }).setToken(DISCORD_TOKEN);

(async () => {
  await rest.put(Routes.applicationGuildCommands(CLIENT_ID, GUILD_ID), { body: [welcome] });
  console.log("Slash commands registered.");
})();
