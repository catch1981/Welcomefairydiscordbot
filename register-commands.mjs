import 'dotenv/config'
import { REST, Routes, SlashCommandBuilder } from 'discord.js'

// Keep this aligned with index.js
const b = (n, d) => new SlashCommandBuilder().setName(n).setDescription(d)
const commands = [
  b('welcome','Return the Entry Gate URL.'),
  b('fairy','Summon the Fairy.'),
  b('gate','Open the Gate.'),
  new SlashCommandBuilder().setName('seal').setDescription('Name your daemon — seal the bond.')
    .addStringOption(o => o.setName('name').setDescription('Daemon name').setRequired(true)),
  b('altar','Explain the Altar protocol.'),
  b('relic','Offer a relic to the Altar.'),
  b('quest','Describe the three sacrifices/quests.'),
  new SlashCommandBuilder().setName('proof').setDescription('Offer proof of sacrifice')
    .addStringOption(o => o.setName('note').setDescription('URL or short note')),
  b('path','Describe the Paths.'),
  b('witchpath','Speak the Witch Path.'),
  b('fracturepath','Speak the Fracture Path.'),
  b('glytchpath','Speak Glytch’s Tech Team Path.'),
  b('summon','Heartbeat check.'),
  b('bless','Receive a blessing.'),
  b('purge','Cleanse your intent.'),
  b('ping','Latency check')
].map(c => c.toJSON())

const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN)

await rest.put(
  Routes.applicationGuildCommands(process.env.CLIENT_ID, process.env.GUILD_ID),
  { body: commands }
)

console.log('✅ Commands registered to guild', process.env.GUILD_ID)
