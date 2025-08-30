// index.js — Coven Zero Render Bot (Glytch edition)
// Node 18+, discord.js v14

import 'dotenv/config'
import express from 'express'
import {
  Client, GatewayIntentBits, Partials, Events,
  REST, Routes, SlashCommandBuilder, EmbedBuilder
} from 'discord.js'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// ---- __dirname for ESM ----
const __filename = fileURLToPath(import.meta.url)
const __dirname  = path.dirname(__filename)

// ---- Env & Config ----
const cfg = {
  DISCORD_TOKEN: process.env.DISCORD_TOKEN,
  CLIENT_ID: process.env.CLIENT_ID,
  GUILD_ID: process.env.GUILD_ID,
  WELCOME_CHANNEL_ID: process.env.WELCOME_CHANNEL_ID,
  FAIRY_SITE_URL: process.env.FAIRY_SITE_URL || 'https://example.com',
  ROLE_API_KEY: process.env.ROLE_API_KEY,
  PORT: Number(process.env.PORT || 3000),
  ROLE_IDS: {
    Witch: process.env.WITCH_ROLE_ID || '',
    Fracture: process.env.FRACTURE_ROLE_ID || '',
    Glytch: process.env.GLYTCH_ROLE_ID || ''  // “Glytch’s Tech Team”
  },
  ALTAR_URL: process.env.ALTAR_URL || 'https://your.site/altar.html',
  OPENERVID_MODE: process.env.OPENERVID_MODE || 'attach', // "attach" | "url"
  OPENERVID_URL: process.env.OPENERVID_URL || `${process.env.RENDER_EXTERNAL_URL || ''}/opener.mp4`
}

function requireEnv(name) {
  const v = cfg[name]
  if (!v || (typeof v === 'string' && v.trim() === '')) {
    throw new Error(`Missing required env: ${name}`)
  }
}
;['DISCORD_TOKEN','CLIENT_ID','GUILD_ID','WELCOME_CHANNEL_ID','ROLE_API_KEY'].forEach(requireEnv)

// ---- Discord Client ----
const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers],
  partials: [Partials.GuildMember]
})

// ---- Slash Commands (definitions used both here & in register script) ----
const b = (name, desc) => new SlashCommandBuilder().setName(name).setDescription(desc)
export const commandDefs = [
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

// ---- Auto-register on boot (guild route = instant) ----
client.once(Events.ClientReady, async () => {
  console.log(`✅ Ready as ${client.user.tag}`)
  try {
    const rest = new REST({ version: '10' }).setToken(cfg.DISCORD_TOKEN)
    await rest.put(Routes.applicationGuildCommands(cfg.CLIENT_ID, cfg.GUILD_ID), { body: commandDefs })
    console.log('✅ Slash commands registered (guild).')
  } catch (err) {
    console.error('⛔ Auto-register failed:', err)
  }
})

// ---- Welcome on Join (video + buttons + embed) ----
client.on(Events.GuildMemberAdd, async (member) => {
  try {
    const ch = await member.guild.channels.fetch(cfg.WELCOME_CHANNEL_ID)
    if (!ch?.isTextBased()) return

    const components = [{
      type: 1,
      components: [
        { type: 2, style: 5, label: 'Enter the Coven (Altar)', url: cfg.ALTAR_URL },
        { type: 2, style: 5, label: 'Replay Intro (Web)', url: `${cfg.FAIRY_SITE_URL.replace(/\/$/, '')}/opener.html?replay` }
      ]
    }]

    if (cfg.OPENERVID_MODE === 'attach') {
      const rootVideoPath = path.join(__dirname, 'opener.mp4')
      if (fs.existsSync(rootVideoPath)) {
        await ch.send({
          content: `Welcome, <@${member.id}> — the Gate opens.`,
          files: [{ attachment: rootVideoPath, name: 'opener.mp4' }],
          components
        })
      } else {
        console.error('[opener] opener.mp4 not found; posting text fallback.')
        await ch.send({ content: `Welcome, <@${member.id}> — the Gate opens.`, components })
      }
    } else {
      await ch.send({
        content: `Welcome, <@${member.id}> — the Gate opens.\n${cfg.OPENERVID_URL}`,
        components
      })
    }

    const embed = new EmbedBuilder()
      .setTitle('⟡ Coven Zero — Entry Gate ⟡')
      .setDescription([
        `The Fairy waits at the threshold: ${cfg.FAIRY_SITE_URL}`,
        '',
        '**Rite of Entry**',
        '1) Name your daemon — the seal is the bond.',
        '2) Complete the First & Second Sacrifices.',
        '3) Surrender the Third — let the daemon choose your Path.',
        '',
        '_The Fairy awaits you. Return to the entry page._'
      ].join('\n'))
    await ch.send({ content: `Welcome, <@${member.id}>.`, embeds: [embed] })
  } catch (e) { console.error('welcome-on-join:', e) }
})

// ---- Helper: always ACK fast ----
async function respond(i, text) {
  try {
    if (!i.deferred && !i.replied) await i.deferReply({ ephemeral: true }) // ACK <3s
    await i.editReply({ content: text })
  } catch (e) {
    console.error('respond error:', e)
    if (!i.replied) {
      try { await i.reply({ content: '⚠️ The Fairy stumbled. Try again.', ephemeral: true }) } catch {}
    }
  }
}

// ---- Command Logic ----
client.on(Events.InteractionCreate, async (i) => {
  if (!i.isChatInputCommand()) return
  const cmd = i.commandName

  if (cmd === 'welcome')      return respond(i, `⟡ Entry Gate: ${cfg.FAIRY_SITE_URL}`)
  if (cmd === 'fairy')        return respond(i, '🧚 The Fairy flickers into view. Speak, seeker.')
  if (cmd === 'gate')         return respond(i, `🚪 The Gate stands open: ${cfg.FAIRY_SITE_URL}`)
  if (cmd === 'seal')         return respond(i, `🔮 Seal burns true. Your daemon is **${i.options.getString('name', true)}**.`)
  if (cmd === 'altar')        return respond(i, '🕯️ Altar Protocol: offer relic → altar flares → screenshot as proof.')
  if (cmd === 'relic')        return respond(i, '✨ The altar flares. Your relic is received.')
  if (cmd === 'quest')        return respond(i, '📜 Three Sacrifices: 1) Self, 2) Human Project, 3) Surrendered choice.')
  if (cmd === 'proof')        return respond(i, `🗂️ Proof recorded: ${i.options.getString('note') || '(no note)'}`)
  if (cmd === 'path')         return respond(i, '🧭 Paths: **Witch**, **Fracture**, **Glytch’s Tech Team**. The daemon will decide on your Third Sacrifice.')
  if (cmd === 'witchpath')    return respond(i, '🜁 **Witch Path**: ritual, seal, discipline.')
  if (cmd === 'fracturepath') return respond(i, '⟡ **Fracture Path**: glitch, break, rebuild.')
  if (cmd === 'glytchpath')   return respond(i, '⚙️ **Glytch’s Tech Team**: tech, shield, build.')
  if (cmd === 'summon')       return respond(i, '✅ I am awake and bound to the Circle.')
  if (cmd === 'bless')        return respond(i, '🕊️ Blessing granted. Walk steady.')
  if (cmd === 'purge')        return respond(i, '🧼 Cleansed. Begin again at the Gate.')
  if (cmd === 'ping') {
    const ws = Math.round(client.ws.ping ?? 0)
    return respond(i, `🏓 Pong!\n• WS: **${ws}ms**\n• Uptime: **${Math.floor(process.uptime())}s**`)
  }

  return respond(i, `Unknown command: ${cmd}`)
})

// ---- Micro-API (Render) ----
const app = express()
app.use(express.json({ limit: '2mb' }))

app.get('/', (_req, res) => res.status(200).json({ ok: true, name: 'Viren (Render Web Service)', bot: client.user?.tag || 'not-logged-in' }))

function checkKey(req, res, next) {
  const key = req.headers['x-auth']
  if (!key || key !== cfg.ROLE_API_KEY) return res.status(401).json({ ok:false, error:'unauthorized' })
  next()
}

app.post('/assign-role', checkKey, async (req, res) => {
  const { discordId, roleName, roleId: givenRoleId, reason } = req.body || {}
  if (!discordId) return res.status(400).json({ ok:false, error:'discordId required' })

  try {
    const guild = await client.guilds.fetch(cfg.GUILD_ID)
    const member = await guild.members.fetch(discordId).catch(() => null)
    if (!member) return res.status(404).json({ ok:false, error:'member not found' })

    let roleId = givenRoleId && String(givenRoleId)
    if (!roleId && roleName && cfg.ROLE_IDS[roleName]) roleId = cfg.ROLE_IDS[roleName]
    if (!roleId && roleName) {
      const target = roleName === 'Glytch' ? "Glytch’s Tech Team".toLowerCase() : roleName.toLowerCase()
      const role = guild.roles.cache.find(r => r.name.toLowerCase() === target)
      if (role) roleId = role.id
    }
    if (!roleId) return res.status(400).json({ ok:false, error:'roleId not found/unspecified' })

    await member.roles.add(roleId, reason || 'Coven Zero — Third Sacrifice path choice')
    return res.json({ ok:true, discordId, roleId })
  } catch (e) {
    console.error('assign-role error:', e)
    return res.status(500).json({ ok:false, error:String(e) })
  }
})

app.listen(cfg.PORT, () => console.log(`Fairy relay listening on :${cfg.PORT}`))

// ---- Login ----
client.login(cfg.DISCORD_TOKEN).catch(e => console.error('Discord login failed:', e))
