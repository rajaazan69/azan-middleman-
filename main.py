const {
  Client, GatewayIntentBits, Partials, ChannelType, PermissionsBitField, PermissionFlagsBits,
  ActionRowBuilder, ModalBuilder, TextInputBuilder, TextInputStyle,
  EmbedBuilder, ButtonBuilder, ButtonStyle, AttachmentBuilder,
  SlashCommandBuilder, REST, Routes
} = require('discord.js');
const express = require('express');
const app = express();
const path = require('path');
app.use('/transcripts', express.static(path.join(__dirname, 'transcripts')));
const fs = require('fs');
require('dotenv').config();
const { MongoClient } = require('mongodb');
const stickyMap = new Map();

const mongoUri = process.env.MONGO_URI;
const mongoClient = new MongoClient(mongoUri);
let tagsCollection;
let transcriptsCollection; // Add this next to tagsCollection
let ticketsCollection;
mongoClient.connect().then(() => {
  const db = mongoClient.db('ticketbot');
  tagsCollection = db.collection('tags');
  transcriptsCollection = db.collection('transcripts'); // ✅ added
ticketsCollection = db.collection('tickets');
clientPointsCollection = db.collection('clientPoints');
  console.log('✅ Connected to MongoDB Atlas');
}).catch(err => {
  console.error('❌ MongoDB connection error:', err);
});

const tagsPath = path.join(__dirname, 'tag.json');
let tags = {};
if (fs.existsSync(tagsPath)) {
  try {
    tags = JSON.parse(fs.readFileSync(tagsPath, 'utf-8'));
    console.log('✅ Tags loaded from tag.json');
  } catch (err) {
    console.error('❌ Failed to parse tag.json:', err);
  }
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,       // ✅ REQUIRED for member joins
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ],
  partials: [Partials.Channel]
});

const PORT = process.env.PORT || 3000;
const OWNER_ID = '1356149794040446998';
const MIDDLEMAN_ROLE = '1373062797545570525';
const PANEL_CHANNEL = '1373048211538841702';
const TICKET_CATEGORY = '1373027564926406796';
const TRANSCRIPT_CHANNEL = '1373058123547283568';
const BASE_URL = process.env.BASE_URL;

app.get('/transcripts/:filename', (req, res) => {
  const filePath = path.join(__dirname, 'transcripts', req.params.filename);
  if (fs.existsSync(filePath)) res.sendFile(filePath);
  else res.status(404).send('Transcript not found.');
});
app.listen(PORT, () => console.log(`Uptime server running on port ${PORT}`));

client.once('ready', async () => {
  console.log(`Bot online as ${client.user.tag}`);
  if (process.env.REGISTER_COMMANDS === 'true') {
    const rest = new REST({ version: '10' }).setToken(process.env.TOKEN);
    const old = await rest.get(Routes.applicationCommands(client.user.id));
    for (const cmd of old) {
      await rest.delete(Routes.applicationCommand(client.user.id, cmd.id));
    }
    console.log('✅ Old commands deleted');
    const commands = [
      new SlashCommandBuilder().setName('setup').setDescription('Send ticket panel').addChannelOption(opt => opt.setName('channel').setDescription('Target channel').setRequired(true)),
      new SlashCommandBuilder().setName('close').setDescription('Close the ticket'),
      new SlashCommandBuilder().setName('delete').setDescription('Delete the ticket'),
      new SlashCommandBuilder().setName('rename').setDescription('Rename the ticket').addStringOption(opt => opt.setName('name').setDescription('New name').setRequired(true)),
      new SlashCommandBuilder().setName('add').setDescription('Add a user to the ticket').addUserOption(opt => opt.setName('user').setDescription('User').setRequired(true)),
      new SlashCommandBuilder().setName('remove').setDescription('Remove a user').addUserOption(opt => opt.setName('user').setDescription('User').setRequired(true)),
      new SlashCommandBuilder().setName('transcript').setDescription('Generate a transcript'),
      new SlashCommandBuilder().setName('tagcreate').setDescription('Create a tag').addStringOption(o => o.setName('name').setDescription('Tag name').setRequired(true)).addStringOption(o => o.setName('message').setDescription('Tag message').setRequired(true)),
      new SlashCommandBuilder().setName('tag').setDescription('Send a saved tag').addStringOption(o => o.setName('name').setDescription('Tag name').setRequired(true)),
      new SlashCommandBuilder().setName('tagdelete').setDescription('Delete a tag').addStringOption(o => o.setName('name').setDescription('Tag name').setRequired(true)),
      new SlashCommandBuilder().setName('taglist').setDescription('List all tags'),
    new SlashCommandBuilder()
  .setName('i')
  .setDescription('Get Roblox user info')
  .addStringOption(opt =>
    opt.setName('username')
      .setDescription('The Roblox username to look up')
      .setRequired(true)
  ),
  new SlashCommandBuilder()
  .setName('kick')
  .setDescription('Kick a member from the server')
  .addUserOption(option =>
    option.setName('user')
      .setDescription('User to kick')
      .setRequired(true))
  .addStringOption(option =>
    option.setName('reason')
      .setDescription('Reason for the kick')
      .setRequired(false))
  .setDefaultMemberPermissions(PermissionFlagsBits.KickMembers),
  new SlashCommandBuilder()
  .setName('resetlb')
  .setDescription('Reset the client leaderboard')
  .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),

new SlashCommandBuilder()
  .setName('ban')
  .setDescription('Ban a member from the server')
  .addUserOption(option =>
    option.setName('user')
      .setDescription('User to ban')
      .setRequired(true))
  .addStringOption(option =>
    option.setName('reason')
      .setDescription('Reason for the ban')
      .setRequired(false))
  .setDefaultMemberPermissions(PermissionFlagsBits.BanMembers),

new SlashCommandBuilder()
  .setName('unban')
  .setDescription('Unban a user by their ID')
  .addStringOption(option =>
    option.setName('userid')
      .setDescription('The ID of the user to unban')
      .setRequired(true))
  .setDefaultMemberPermissions(PermissionFlagsBits.BanMembers),

new SlashCommandBuilder()
  .setName('timeout')
  .setDescription('Timeout a member for a set number of minutes')
  .addUserOption(option =>
    option.setName('user')
      .setDescription('User to timeout')
      .setRequired(true))
  .addStringOption(option =>
  option.setName('duration')
    .setDescription('e.g. 10m, 1h, 2d')
    .setRequired(true))
  .addStringOption(option =>
    option.setName('reason')
      .setDescription('Reason for timeout')
      .setRequired(false))
  .setDefaultMemberPermissions(PermissionFlagsBits.ModerateMembers),

new SlashCommandBuilder()
  .setName('warn')
  .setDescription('Warn a user')
  .addUserOption(option =>
    option.setName('user')
      .setDescription('User to warn')
      .setRequired(true))
  .addStringOption(option =>
    option.setName('reason')
      .setDescription('Reason for the warning')
      .setRequired(false))
  .setDefaultMemberPermissions(PermissionFlagsBits.KickMembers),

new SlashCommandBuilder()
  .setName('lock')
  .setDescription('Lock the current channel')
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageChannels),

new SlashCommandBuilder()
  .setName('unlock')
  .setDescription('Unlock the current channel')
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageChannels),
    
  new SlashCommandBuilder()
  .setName('setsticky')
  .setDescription('Set a sticky message for a specific channel')
  .addChannelOption(option =>
    option.setName('channel')
      .setDescription('Select the channel to set the sticky message in')
      .setRequired(true))
  .addStringOption(option =>
    option.setName('message')
      .setDescription('The sticky message content')
      .setRequired(true))
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages),
  new SlashCommandBuilder()
  .setName('untimeout')
  .setDescription('Remove timeout from a user')
  .addUserOption(option =>
    option.setName('user')
      .setDescription('User to remove timeout from')
      .setRequired(true))
  .addStringOption(option =>
    option.setName('reason')
      .setDescription('Reason for removing timeout')
      .setRequired(false))
  .setDefaultMemberPermissions(PermissionFlagsBits.ModerateMembers),
    new SlashCommandBuilder()
    .setName('servers')
    .setDescription('Get Roblox server join options')
    .addStringOption(option =>
      option.setName('game')
        .setDescription('Select the game')
        .setRequired(true)
        .addChoices(
          { name: 'GAG', value: 'gag' },
          { name: 'MM2', value: 'mm2' },
          { name: 'SAB', value: 'sab' }
        ))
].map(command => command.toJSON());
    await rest.put(Routes.applicationCommands(client.user.id), { body: commands });
    console.log('✅ Slash commands registered');
  } else {
    console.log('🟡 Skipping command registration (REGISTER_COMMANDS is false)');
  }

client.on('interactionCreate', async interaction => {
  try {
    const { commandName, options, channel, guild } = interaction;

if (interaction.isChatInputCommand()) {
  if (commandName === 'setup') {
    const target = options.getChannel('channel');

    const panelEmbed = new EmbedBuilder()
      .setColor('#000000')
      .setTitle('Azan’s Middleman Service')
      .setDescription(
        `To request a middleman from this server\n` +
        `click the \`Request Middleman\` button below.\n\n` +

        `**How does a Middleman Work?**\n` +
        `Example: Trade is Harvester (MM2) for Robux.\n` +
        `1. Seller gives Harvester to middleman.\n` +
        `2. Buyer pays seller robux (after middleman confirms receiving mm2).\n` +
        `3. Middleman gives buyer Harvester (after seller received robux).\n\n` +

        `**Important**\n` +
        `• Troll tickets are not allowed. Once the trade is completed you must vouch your middleman in their respective servers.\n` +
        `• If you have trouble getting a user's ID click [here](https://youtube.com/shorts/pMG8CuIADDs?feature=shared).\n` +
        `• Make sure to read <#1373027499738398760> before making a ticket.`
      );

    const btn = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId('openTicket')
        .setLabel('Request Middleman')
        .setStyle(ButtonStyle.Primary)
    );

    await target.send({ embeds: [panelEmbed], components: [btn] });
    await interaction.reply({ content: '✅ Setup complete.', ephemeral: true }).catch(() => {});
  }
}

      if (commandName === 'tagcreate') {
  await interaction.deferReply({ ephemeral: true }).catch(() => {});
  const name = options.getString('name');
  const message = options.getString('message');
  try {
    await tagsCollection.updateOne(
      { name },
      { $set: { message } },
      { upsert: true }
    );
    await interaction.editReply({ content: `✅ Tag \`${name}\` saved.` });
  } catch (err) {
    console.error('❌ Tag create failed:', err);
    await interaction.editReply({ content: '❌ Failed to create tag.' });
  }
} // ✅ <---- This is needed!

      if (commandName === 'tag') {
        const name = options.getString('name');
        try {
  const tag = await tagsCollection.findOne({ name });
  if (tag) {
    await interaction.reply({ content: tag.message.slice(0, 2000) });
  } else {
    await interaction.reply({ content: `❌ Tag \`${name}\` not found.` });
  }
} catch (err) {
  console.error('❌ Tag read error:', err);
  await interaction.reply({ content: '❌ Error reading tag.' });
}
      }
        if (commandName === 'resetlb') {
  const OWNER_ID = '1356149794040446998'; // Replace with your Discord ID

  const user = interaction.user;           // get user from interaction
  const member = interaction.member;       // get member from interaction (guild member)

  const isOwner = user.id === OWNER_ID;
  const isAdmin = member.permissions.has(PermissionsBitField.Flags.Administrator);

  if (!isOwner && !isAdmin) {
    return interaction.reply({ content: '❌ You do not have permission to reset the leaderboard.', ephemeral: true });
  }

  try {
    // Clear all points
    await clientPointsCollection.deleteMany({});

    // Update leaderboard message
    const leaderboardChannel = await client.channels.fetch(process.env.LEADERBOARD_CHANNEL_ID);
    const leaderboardMessage = await leaderboardChannel.messages.fetch(process.env.LEADERBOARD_MESSAGE_ID);

    const embed = new EmbedBuilder()
      .setTitle('**🏆 Client Leaderboard**')
      .setDescription('No points recorded yet!')
      .setColor('#FFD700')
      .setTimestamp();

    await leaderboardMessage.edit({ embeds: [embed] });

    await interaction.reply({ content: '✅ Leaderboard has been reset.', ephemeral: true });
  } catch (error) {
    console.error('❌ Error resetting leaderboard:', error);
    await interaction.reply({ content: '❌ Failed to reset leaderboard.', ephemeral: true });
  }
}

      if (commandName === 'tagdelete') {
        await interaction.deferReply({ ephemeral: true }).catch(() => {});
        const name = options.getString('name');
       try {
  const result = await tagsCollection.deleteOne({ name });
  if (result.deletedCount === 0) {
    await interaction.editReply({ content: `❌ Tag \`${name}\` not found.` });
  } else {
    await interaction.editReply({ content: `🗑️ Tag \`${name}\` deleted.` });
  }
} catch (err) {
  console.error('❌ Tag delete error:', err);
  await interaction.editReply({ content: '❌ Failed to delete tag.' });
}
      }

      if (commandName === 'taglist') {
        try {
  const tags = await tagsCollection.find({}).toArray();
  const list = tags.map(t => `• \`${t.name}\``).join('\n') || 'No tags found.';
  await interaction.reply({ content: list });
} catch (err) {
  console.error('❌ Tag list error:', err);
  await interaction.reply({ content: '❌ Failed to fetch tag list.' });
}
      }

      if (commandName === 'close') {
  console.log('[DEBUG] /close command triggered');

  if (!interaction.deferred && !interaction.replied) {
    try {
      await interaction.deferReply({ ephemeral: true });
      console.log('[DEBUG] Interaction deferred');
    } catch (err) {
      console.error('[ERROR] Could not defer interaction:', err);
      return;
    }
  }

  try {
    const parentId = channel.parentId || channel.parent?.id;
    if (parentId !== TICKET_CATEGORY) {
      return interaction.editReply({
        content: '❌ You can only close ticket channels!'
      });
    }

    const perms = channel.permissionOverwrites.cache;
    const ticketOwner = [...perms.values()].find(po =>
      po.allow.has(PermissionsBitField.Flags.ViewChannel) &&
      po.id !== OWNER_ID &&
      po.id !== MIDDLEMAN_ROLE &&
      po.id !== guild.id
    )?.id;

    // Lock the ticket - don't await each one individually
    const updates = [...perms.entries()]
      .filter(([id]) => ![OWNER_ID, MIDDLEMAN_ROLE, guild.id].includes(id))
      .map(([id]) =>
        channel.permissionOverwrites.edit(id, {
          SendMessages: false,
          ViewChannel: false
        }).catch(err => {
          console.warn(`⚠️ Could not update permissions for ${id}:`, err.code || err.message);
        })
      );

    await Promise.allSettled(updates);

    const embed = new EmbedBuilder()
      .setTitle('🔒 Ticket Closed')
      .setDescription('Select an option below to generate the transcript or delete the ticket.')
      .addFields(
        { name: 'Ticket Name', value: channel.name, inline: true },
        {
          name: 'Owner',
          value: ticketOwner ? `<@${ticketOwner}> (${ticketOwner})` : 'Unknown',
          inline: true
        }
      )
      .setColor('#2B2D31')
      .setFooter({
        text: `Closed by ${interaction.user.tag}`,
        iconURL: interaction.user.displayAvatarURL()
      })
      .setTimestamp();

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId('transcript').setLabel('TRANSCRIPT').setStyle(ButtonStyle.Secondary),
      new ButtonBuilder().setCustomId('delete').setLabel('DELETE').setStyle(ButtonStyle.Danger),
    new ButtonBuilder()
    .setCustomId('log_points')
    .setLabel('LOG POINTS')
    .setStyle(ButtonStyle.Success)
);

    await interaction.editReply({ embeds: [embed], components: [row] });
    console.log('[DEBUG] Close panel sent');

  } catch (err) {
    console.error('❌ /close command error:', err);
    try {
      if (!interaction.replied && !interaction.deferred) {
        await interaction.reply({ content: '❌ Failed to close ticket.', ephemeral: true });
      } else {
        await interaction.editReply({ content: '❌ Failed to close ticket.' });
      }
    } catch (editErr) {
      console.error('❌ Failed to send error reply:', editErr);
    }
  }
}
      if (commandName === 'delete') {
        const parentId = channel.parentId || channel.parent?.id;
        if (parentId === TICKET_CATEGORY) await channel.delete();
        else await interaction.reply({ content: '❌ You can only delete ticket channels!', ephemeral: true });
      }

      if (commandName === 'rename') {
        const newName = options.getString('name');
        if ((channel.parentId || channel.parent?.id) !== TICKET_CATEGORY) return interaction.reply({ content: '❌ You can only rename ticket channels!', ephemeral: true });
        await channel.setName(newName);
        return interaction.reply({ content: `✅ Renamed to \`${newName}\``, ephemeral: true });
      }

      if (commandName === 'add') {
        const user = options.getUser('user');
        if ((channel.parentId || channel.parent?.id) !== TICKET_CATEGORY) return interaction.reply({ content: '❌ You can only add users in ticket channels!', ephemeral: true });
        await channel.permissionOverwrites.edit(user.id, { SendMessages: true, ViewChannel: true });
        await interaction.reply({ content: `✅ ${user} added.`, ephemeral: true });
      }

      if (commandName === 'remove') {
        const user = options.getUser('user');
        if ((channel.parentId || channel.parent?.id) !== TICKET_CATEGORY) return interaction.reply({ content: '❌ You can only remove users in ticket channels!', ephemeral: true });
        await channel.permissionOverwrites.delete(user.id);
        await interaction.reply({ content: `✅ ${user} removed.`, ephemeral: true });
      }

      if (commandName === 'transcript') {
        if ((channel.parentId || channel.parent?.id) !== TICKET_CATEGORY) return interaction.reply({ content: '❌ You can only generate transcripts in ticket channels!', ephemeral: true });
        await interaction.deferReply({ ephemeral: true }).catch(() => {});
        await handleTranscript(interaction, channel);
      }
    if (commandName === 'i') {
  const username = options.getString('username');
  await interaction.deferReply();

  try {
    const userRes = await fetch(`https://users.roblox.com/v1/usernames/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usernames: [username], excludeBannedUsers: false })
    });

    const userData = await userRes.json();
    const user = userData.data?.[0];

    if (!user) {
      return interaction.editReply({ content: '❌ User not found.' });
    }

    const [profileRes, followersRes, followingRes, avatarRes] = await Promise.all([
      fetch(`https://users.roblox.com/v1/users/${user.id}`),
      fetch(`https://friends.roblox.com/v1/users/${user.id}/followers/count`),
      fetch(`https://friends.roblox.com/v1/users/${user.id}/followings/count`),
      fetch(`https://thumbnails.roblox.com/v1/users/avatar?userIds=${user.id}&size=720x720&format=Png&isCircular=false`)
    ]);

    const profile = await profileRes.json();
    const followers = await followersRes.json();
    const following = await followingRes.json();
    const avatarData = await avatarRes.json();
    const avatarUrl = avatarData.data?.[0]?.imageUrl || null;

    const createdDate = new Date(profile.created);
    const now = new Date();
    const yearsOld = ((now - createdDate) / (1000 * 60 * 60 * 24 * 365)).toFixed(1);

    const embed = new EmbedBuilder()
      .setTitle(`Roblox User Information`)
      .setColor('#000000')
      .setThumbnail(`https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds=${user.id}&size=150x150&format=Png&isCircular=true`)
      .addFields(
        { name: 'Display Name', value: `${profile.displayName}`, inline: false },
        { name: 'Username', value: `${profile.name}`, inline: false },
        { name: 'User ID', value: `${user.id}`, inline: false },
        { name: '\u200B', value: '\u200B', inline: false },
        { name: 'Account Created', value: `<t:${Math.floor(createdDate.getTime() / 1000)}:F>`, inline: false },
        { name: 'Account Age', value: `${yearsOld} years`, inline: false },
        { name: '\u200B', value: '\u200B', inline: false },
        { name: 'Followers', value: `${followers?.count?.toLocaleString() || 'N/A'}`, inline: false },
        { name: 'Following', value: `${following?.count?.toLocaleString() || 'N/A'}`, inline: false }
      )
      .setFooter({ text: 'Roblox Profile Info', iconURL: 'https://tr.rbxcdn.com/4f82333f5f54d234e95d1f81251a67dc/150/150/Image/Png' })
      .setTimestamp();

    if (avatarUrl) embed.setImage(avatarUrl);

    const button = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setLabel('View Profile')
        .setStyle(ButtonStyle.Link)
        .setURL(`https://www.roblox.com/users/${user.id}/profile`)
    );

    await interaction.editReply({ embeds: [embed], components: [button] });

  } catch (err) {
    console.error('❌ Roblox user info error:', err);
    await interaction.editReply({ content: '❌ Failed to fetch user info.' });
  }
}
if (commandName === 'ban') {
  const target = options.getMember('user');
  const reason = options.getString('reason') || 'No reason provided.';

  if (!target) {
    return interaction.reply({ content: '❌ Member not found.', ephemeral: true });
  }

  try {
    await target.ban({ reason });

    const embed = new EmbedBuilder()
      .setTitle('User Banned')
      .setColor('#000000')
      .addFields(
        { name: '**User**', value: `${target.user.tag} (<@${target.id}>)`, inline: true },
        { name: '**Reason**', value: reason }
      )
      .setFooter({ text: `Moderator: ${interaction.user.tag}` })
      .setTimestamp();

    await interaction.reply({ embeds: [embed] });
  } catch (err) {
    console.error('❌ Ban error:', err);
    await interaction.reply({ content: '❌ Failed to ban the user.', ephemeral: true });
  }
}
if (commandName === 'kick') {
  const target = options.getMember('user');
  const reason = options.getString('reason') || 'No reason provided.';

  if (!target) {
    return interaction.reply({ content: '❌ Member not found.', ephemeral: true });
  }

  try {
    await target.kick(reason);

    const embed = new EmbedBuilder()
      .setTitle('User Kicked')
      .setColor('#000000')
      .addFields(
        { name: '**User**', value: `${target.user.tag} (<@${target.id}>)`, inline: true },
        { name: '**Reason**', value: reason }
      )
      .setFooter({ text: `Moderator: ${interaction.user.tag}` })
      .setTimestamp();

    await interaction.reply({ embeds: [embed] });
  } catch (err) {
    console.error('❌ Kick error:', err);
    await interaction.reply({ content: '❌ Failed to kick the user.', ephemeral: true });
  }
}
if (commandName === 'lock') {
  try {
    await channel.permissionOverwrites.edit(guild.roles.everyone, {
      SendMessages: false
    });

    const embed = new EmbedBuilder()
      .setTitle('Channel Locked')
      .setColor('#000000')
      .setDescription(`**Channel:** ${channel.name}\n**Locked by:** ${interaction.user.tag}`)
      .setTimestamp();

    await interaction.reply({ embeds: [embed] });
  } catch (err) {
    console.error('❌ Lock error:', err);
    await interaction.reply({ content: '❌ Failed to lock the channel.', ephemeral: true });
  }
}
if (commandName === 'timeout') {
  await interaction.deferReply().catch(() => {});

  const user = options.getUser('user');
  const member = guild.members.cache.get(user.id);
  const duration = options.getString('duration'); // e.g. "10m", "1h"
  const reason = options.getString('reason') || 'No reason provided.';

  const ms = require('ms');
  const time = ms(duration);

  if (!time || isNaN(time)) {
    return await interaction.editReply({ content: '❌ Invalid duration format.' });
  }

  try {
    await member.timeout(time, reason);

    const embed = new EmbedBuilder()
      .setTitle('User Timed Out')
      .setColor('#000000')
      .setDescription(
        `**User:** <@${user.id}> (${user.tag})\n` +
        `**Duration:** ${duration}\n` +
        `**Reason:** ${reason}\n` +
        `**Moderator:** ${interaction.user.tag}`
      )
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  } catch (err) {
    console.error('❌ Timeout error:', err);
    await interaction.editReply({ content: '❌ Failed to timeout the user.' });
  }
}
if (commandName === 'unban') {
  const userId = options.getString('userid');
  const reason = options.getString('reason') || 'No reason provided.';

  try {
    await guild.bans.remove(userId, reason);

    const embed = new EmbedBuilder()
      .setTitle('User Unbanned')
      .setColor('#000000')
      .addFields(
        { name: '**User ID**', value: userId, inline: true },
        { name: '**Reason**', value: reason }
      )
      .setFooter({ text: `Moderator: ${interaction.user.tag}` })
      .setTimestamp();

    await interaction.reply({ embeds: [embed] });
  } catch (err) {
    console.error('❌ Unban error:', err);
    await interaction.reply({ content: '❌ Failed to unban the user.', ephemeral: true });
  }
}
if (commandName === 'unlock') {
  try {
    await channel.permissionOverwrites.edit(guild.roles.everyone, {
      SendMessages: true
    });

    const embed = new EmbedBuilder()
      .setTitle('Channel Unlocked')
      .setColor('#000000')
      .setDescription(`**Channel:** ${channel.name}\n**Unlocked by:** ${interaction.user.tag}`)
      .setTimestamp();

    await interaction.reply({ embeds: [embed] });
  } catch (err) {
    console.error('❌ Unlock error:', err);
    await interaction.reply({ content: '❌ Failed to unlock the channel.', ephemeral: true });
  }
}
if (commandName === 'warn') {
  await interaction.deferReply().catch(() => {});

  const user = options.getUser('user');
  const reason = options.getString('reason') || 'No reason provided.';

  const embed = new EmbedBuilder()
    .setTitle('User Warned')
    .setColor('#000000')
    .setDescription(
      `**User:** <@${user.id}> (${user.tag})\n` +
      `**Reason:** ${reason}\n` +
      `**Moderator:** ${interaction.user.tag}`
    )
    .setTimestamp();

  try {
    await interaction.editReply({ embeds: [embed] });
  } catch (err) {
    console.error('❌ Warn error:', err);
    await interaction.editReply({ content: '❌ Failed to send warning embed.' });
  }
}
if (commandName === 'untimeout') {
  await interaction.deferReply().catch(() => {});

  const user = options.getUser('user');
  const member = guild.members.cache.get(user.id);
  const reason = options.getString('reason') || 'No reason provided.';

  if (!member) {
    return await interaction.editReply({ content: '❌ Member not found in this server.' });
  }

  try {
    await member.timeout(null, reason);

    const embed = new EmbedBuilder()
      .setTitle('Timeout Removed')
      .setColor('#000000')
      .setDescription(
        `**User:** <@${user.id}> (${user.tag})\n` +
        `**Reason:** ${reason}\n` +
        `**Moderator:** ${interaction.user.tag}`
      )
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  } catch (err) {
    console.error('❌ Untimeout error:', err);
    await interaction.editReply({ content: '❌ Failed to remove timeout from the user.' });
  }
}
    

    // ✅ BUTTON: Open Modal
    if (interaction.isButton() && interaction.customId === 'openTicket') {
      const modal = new ModalBuilder()
        .setCustomId('ticketModal')
        .setTitle('Middleman Request')
        .addComponents(
          new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('q1').setLabel("What's the trade?").setStyle(TextInputStyle.Short).setRequired(true)),
          new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('q2').setLabel("What's your side?").setStyle(TextInputStyle.Paragraph).setRequired(true)),
          new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('q3').setLabel("What's their side?").setStyle(TextInputStyle.Paragraph).setRequired(true)),
          new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('q4').setLabel("Their Discord ID?").setStyle(TextInputStyle.Short).setRequired(true))
        );
      await interaction.showModal(modal).catch(console.error);
    }

    // ✅ BUTTON: Transcript Fix
if (interaction.isButton() && interaction.customId === 'transcript') {
      const parentId = interaction.channel.parentId || interaction.channel.parent?.id;
      if (parentId !== TICKET_CATEGORY) {
        return interaction.reply({ content: '❌ You can only use this inside ticket channels.', ephemeral: true });
      }
      await interaction.deferReply({ ephemeral: true }).catch(() => {});
      await handleTranscript(interaction, interaction.channel);
    }

    // ✅ BUTTON: Delete
    if (interaction.isButton() && interaction.customId === 'delete') {
      await interaction.channel.delete().catch(console.error);
    }
    if (interaction.isButton() && interaction.customId === 'log_points') {
  try {
    const channel = interaction.channel;
    const guild = interaction.guild;

    // Check if inside ticket category
    const parentId = channel.parentId || channel.parent?.id;
    if (parentId !== TICKET_CATEGORY) {
      return interaction.reply({ content: '❌ This button can only be used inside ticket channels.', ephemeral: true });
    }

    // Defer reply so we can do async operations without timeout or "already replied" errors
    await interaction.deferReply({ ephemeral: true });

    // Get ticket data from DB
    const ticketData = await ticketsCollection.findOne({ channelId: channel.id });
    if (!ticketData) {
      return interaction.editReply({ content: '❌ Could not find ticket data.' });
    }

    const userIds = [ticketData.user1, ticketData.user2].filter(Boolean);

    // Add points for each user
    for (const userId of userIds) {
      const existing = await clientPointsCollection.findOne({ userId });
      if (existing) {
        await clientPointsCollection.updateOne({ userId }, { $inc: { points: 1 } });
      } else {
        await clientPointsCollection.insertOne({ userId, points: 1 });
      }
    }

    // Fetch leaderboard message
    const leaderboardChannel = await guild.channels.fetch(process.env.LEADERBOARD_CHANNEL_ID);
    if (!leaderboardChannel) {
      return interaction.editReply({ content: '❌ Leaderboard channel not found.' });
    }
    const leaderboardMessage = await leaderboardChannel.messages.fetch(process.env.LEADERBOARD_MESSAGE_ID);

    // Get sorted top users
    const topUsers = await clientPointsCollection.find().sort({ points: -1 }).limit(10).toArray();

    const leaderboardText = topUsers.map((user, i) =>
      `**#${i + 1}** <@${user.userId}> — **${user.points}** point${user.points === 1 ? '' : 's'}`
    ).join('\n');

    const embed = new EmbedBuilder()
      .setTitle('🏆 Top Clients This Month')
      .setDescription(leaderboardText || 'No data yet.')
      .setColor('#2B2D31')
      .setFooter({ text: 'Client Leaderboard' })
      .setTimestamp();

    await leaderboardMessage.edit({ embeds: [embed] });

    // Reply to user confirming
    await interaction.editReply({ content: `✅ Logged 1 point for <@${userIds.join('>, <@')}>` });

  } catch (err) {
    console.error('❌ Error logging points:', err);
    if (!interaction.replied && !interaction.deferred) {
      await interaction.reply({ content: '❌ Something went wrong while logging points.', ephemeral: true });
    } else {
      await interaction.editReply({ content: '❌ Something went wrong while logging points.' }).catch(() => {});
    }
  }
}

    if (interaction.isModalSubmit() && interaction.customId === 'ticketModal') {
      // Prevent multiple tickets per user
const existing = interaction.guild.channels.cache.find(c =>
  c.parentId === TICKET_CATEGORY &&
  c.permissionOverwrites.cache.has(interaction.user.id)
);

if (existing) {
  return interaction.reply({ content: `❌ You already have an open ticket: ${existing}`, ephemeral: true });
}
      const q1 = interaction.fields.getTextInputValue('q1');
      const q2 = interaction.fields.getTextInputValue('q2');
      const q3 = interaction.fields.getTextInputValue('q3');
      const q4 = interaction.fields.getTextInputValue('q4');
const isValidId = /^\d{17,19}$/.test(q4);
const targetMention = isValidId ? `<@${q4}>` : 'Unknown User';

// Prepare permission overwrites array
const permissionOverwrites = [
  { id: interaction.guild.id, deny: [PermissionsBitField.Flags.ViewChannel] },
  { id: interaction.user.id, allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages] },
  { id: OWNER_ID, allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages] },
  { id: MIDDLEMAN_ROLE, allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages] }
];


// Add the target user to permission overwrites if ID is valid and member exists
if (isValidId) {
  const member = interaction.guild.members.cache.get(q4);
  if (member) {
    permissionOverwrites.push({
      id: q4,
      allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages]
    });
  }
}

const ticket = await interaction.guild.channels.create({
  name: `ticket-${interaction.user.username}`,
  type: ChannelType.GuildText,
  parent: TICKET_CATEGORY,
  permissionOverwrites
});
await ticketsCollection.insertOne({
  channelId: ticket.id,
  user1: interaction.user.id,
  user2: q4
});

const embed = new EmbedBuilder()
  .setTitle('Middleman Request')
  .setColor('#FFFFFF')
  .setThumbnail(interaction.user.displayAvatarURL({ dynamic: true }))
  .addFields(
    { name: '**User 1**', value: `<@${interaction.user.id}>`, inline: true },
    { name: '**User 2**', value: `${targetMention}`, inline: true },
    { name: '\u200B', value: '\u200B' }, // empty spacer

    { name: '**Trade Details**', value: `> ${q1}` },
    { name: '**User 1 is giving**', value: `> ${q2}` },
    { name: '**User 2 is giving**', value: `> ${q3}` },
  )
  .setFooter({ text: `Ticket by ${interaction.user.tag}`, iconURL: interaction.user.displayAvatarURL() })
  .setTimestamp();
const infoEmbed = new EmbedBuilder()
  .setColor('#FFFFFF')
  .setDescription(
    `Please wait for our **Middleman Team** to assist you.\n` +
    `Make sure to abide by all the rules and **vouch when the trade is over**.`
  );
        await ticket.send({
  content: `<@${interaction.user.id}> made a ticket with ${isValidId ? `<@${q4}>` : '`Unknown User`'}.\nPlease wait until <@${OWNER_ID}> assists you.`,
  embeds: [infoEmbed, embed]
});
          

        await interaction.reply({ content: `✅ Ticket created: ${ticket}`, ephemeral: true });
      
    }

  } catch (err) {
    console.error('❌ Interaction error:', err);
  }
});

async function handleTranscript(interaction, channel) {
  try {
    const messages = await channel.messages.fetch({ limit: 100 });
    const sorted = messages.sort((a, b) => a.createdTimestamp - b.createdTimestamp);
    const participants = new Map();

    for (const m of sorted.values()) {
      if (!m.author?.bot) {
        participants.set(m.author.id, (participants.get(m.author.id) || 0) + 1);
      }
    }

    const { createTranscript } = require('discord-html-transcripts');
    const transcriptAttachment = await createTranscript(channel, {
      limit: -1,
      returnType: 'attachment',
      fileName: `${channel.id}.html`,
      poweredBy: false,
      saveImages: true
    });

    const filepath = path.join(__dirname, 'transcripts');
    if (!fs.existsSync(filepath)) fs.mkdirSync(filepath);

    const htmlPath = path.join(filepath, transcriptAttachment.name);
    fs.writeFileSync(htmlPath, transcriptAttachment.attachment);

    if (transcriptsCollection) {
      await transcriptsCollection.insertOne({
        channelId: channel.id,
        channelName: channel.name,
        participants: [...participants.entries()].map(([id, count]) => ({
          userId: id,
          count
        })),
        content: transcriptAttachment.attachment.toString('utf-8'),
        createdAt: new Date()
      });
    }

    const htmlLink = `${BASE_URL}/transcripts/${transcriptAttachment.name}`;

    const txtLines = sorted.map(m =>
      `[${new Date(m.createdTimestamp).toISOString()}] ${m.author.tag}: ${m.cleanContent || '[Embed/Attachment]'}`
    ).join('\n');
    const txtPath = path.join(filepath, `transcript-${channel.id}.txt`);
    fs.writeFileSync(txtPath, txtLines);

    const embed = new EmbedBuilder()
      .setTitle('📄 Transcript Ready')
      .setDescription('Your ticket transcript is now ready.')
      .addFields(
        { name: 'Ticket Name', value: channel.name, inline: true },
        { name: 'Ticket ID', value: channel.id.toString(), inline: true },
        {
          name: 'Participants',
          value: [...participants.entries()]
            .map(([id, count]) => `<@${id}> — \`${count}\` messages`)
            .join('\n')
            .slice(0, 1024) || 'None',
          inline: false
        }
      )
      .setColor('#000000')
      .setTimestamp();

    const buttonRow = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setLabel('View HTML Transcript')
        .setStyle(ButtonStyle.Link)
        .setURL(htmlLink)
    );

    await interaction.editReply({
      embeds: [embed],
      files: [new AttachmentBuilder(txtPath)],
      components: [buttonRow]
    }).catch(() => {});

    const logChannel = client.channels.cache.get(TRANSCRIPT_CHANNEL);
    if (logChannel) {
      await logChannel.send({
        embeds: [embed],
        files: [new AttachmentBuilder(txtPath)],
        components: [buttonRow]
      });
    }

  } catch (err) {
    console.error('❌ Transcript generation failed:', err);
    if (!interaction.replied && !interaction.deferred) {
      await interaction.reply({ content: '❌ Failed to generate transcript.', ephemeral: true });
    } else {
      await interaction.editReply({ content: '❌ Failed to generate transcript.' }).catch(() => {});
    }
  }
}
});
client.on('interactionCreate', async (interaction) => {
  if (!interaction.isChatInputCommand()) return;

  if (interaction.commandName === 'setsticky') {
    const channel = interaction.options.getChannel('channel');
    const message = interaction.options.getString('message');

    // Send the sticky message now
    const sentMessage = await channel.send({ content: message });

    // Save it in stickyMap
    stickyMap.set(channel.id, {
      message,
      messageId: sentMessage.id
    });

    await interaction.reply({ content: `✅ Sticky message set in ${channel}`, ephemeral: true });
  }
});
client.on('messageCreate', async (message) => {
  if (message.author.bot || message.channel.type !== ChannelType.GuildText) return;

  const sticky = stickyMap.get(message.channel.id);
  if (!sticky) return;

  try {
    const oldMsg = await message.channel.messages.fetch(sticky.messageId).catch(() => {});
    if (oldMsg) await oldMsg.delete().catch(() => {});

    const newMsg = await message.channel.send({ content: sticky.message });

    stickyMap.set(message.channel.id, {
      message: sticky.message,
      messageId: newMsg.id
    });
  } catch (err) {
    console.error('Sticky message error:', err);
  }
});
client.on('interactionCreate', async (interaction) => {
  const parentId = interaction.channel?.parentId || interaction.channel?.parent?.id;

  // 📄 Transcript slash command
  if (interaction.isChatInputCommand() && interaction.commandName === 'transcript') {
    if (parentId !== TICKET_CATEGORY) {
      return interaction.reply({
        content: '❌ You can only use this inside ticket channels.',
        ephemeral: true
      });
    }

    await interaction.deferReply({ ephemeral: true }).catch(() => {});
    return handleTranscript(interaction, interaction.channel);
  }

  // 📄 Transcript button
  if (interaction.isButton() && interaction.customId === 'generate_transcript') {
    if (parentId !== TICKET_CATEGORY) {
      return interaction.reply({
        content: '❌ You can only use this inside ticket channels.',
        ephemeral: true
      });
    }

    await interaction.deferReply({ ephemeral: true }).catch(() => {});
    return handleTranscript(interaction, interaction.channel);
  }
});
const gameData = {
  gag: {
    name: 'GAG',
    publicLink: 'https://www.roblox.com/games/126884695634066/Grow-a-Garden?sortFilter=3',
    privateLink: 'https://www.roblox.com/share?code=2daaf72e32f63840b588d65a5cff53a7&type=Server',
    thumbnail: 'https://cdn.discordapp.com/attachments/1373070247795495116/1396644967665111142/IMG_6743.jpg'
  },
  mm2: {
    name: 'MM2',
    publicLink: 'https://www.roblox.com/games/66654135/Murder-Mystery-2?sortFilter=3',
    privateLink: 'https://www.roblox.com/share?code=c1ac8abd3c27354e9db3979aad38b842&type=Server',
    thumbnail: 'https://cdn.discordapp.com/attachments/1373070247795495116/1396644976829661194/IMG_6744.jpg'
  },
  sab: {
    name: 'SAB (Steal a Brainrot)',
    publicLink: 'https://www.roblox.com/games/109983668079237/Steal-a-Brainrot?sortFilter=3',
    privateLink: 'https://www.roblox.com/share?code=d99e8e73482e8342a3aa30fb59973322&type=Server',
    thumbnail: 'https://cdn.discordapp.com/attachments/1373070247795495116/1396644973134348288/IMG_6745.jpg'
  }
};
// Preload Discord CDN thumbnails once at startup to avoid Discord cache delay
const https = require('https');

Object.values(gameData).forEach(game => {
  if (game.thumbnail.startsWith('https://cdn.discordapp.com')) {
    https.get(game.thumbnail, res => {
      console.log(`Preloaded: ${game.name} thumbnail with status ${res.statusCode}`);
    }).on('error', err => {
      console.error(`Failed to preload: ${game.name}`, err.message);
    });
  }
});


client.on('interactionCreate', async (interaction) => {
  if (interaction.isChatInputCommand() && interaction.commandName === 'servers') {
    const game = interaction.options.getString('game');
    const channel = interaction.channel;

    const parentId = channel?.parentId || channel?.parent?.id;
    if (parentId !== TICKET_CATEGORY) {
      return interaction.reply({
        content: '❌ This command can only be used inside ticket channels.',
        ephemeral: true
      });
    }

    const selectedGame = gameData[game];

    const embed = new EmbedBuilder()
      .setTitle(`Server Options for ${selectedGame.name}`)
      .setDescription('**Please Choose Which Server You Would Be The Most Comfortable For The Trade In. Confirm The Middleman Which Server To Join**')
      .setImage(selectedGame.thumbnail)
      .setColor('#000000')
      .setTimestamp();

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId(`public_${game}`)
        .setLabel('Join Public Server')
        .setStyle(ButtonStyle.Primary),
      new ButtonBuilder()
        .setCustomId(`private_${game}`)
        .setLabel('Join Private Server')
        .setStyle(ButtonStyle.Secondary)
    );

    await interaction.reply({ embeds: [embed], components: [row] });
  }

  if (interaction.isButton()) {
  try {
    const [type, game] = interaction.customId.split('_');
    const selectedGame = gameData[game];
    if (!selectedGame) return;

    const isPublic = type === 'public';
    const embed = new EmbedBuilder()
      .setTitle('Server Chosen')
      .setColor('#000000')
      .setDescription(`**${interaction.user} has chosen to trade in the ${isPublic ? 'Public' : 'Private'} Server.**`)
      .addFields({
        name: '🔗 Click to Join:',
        value: `[${isPublic ? 'Public' : 'Private'} Server Link](${isPublic ? selectedGame.publicLink : selectedGame.privateLink})`
      })
      .setImage(selectedGame.thumbnail)
      .setTimestamp();

    // Safely reply if not already replied
    if (!interaction.deferred && !interaction.replied) {
  await interaction.deferReply({ ephemeral: false });
}

await interaction.editReply({ embeds: [embed] });
    
  } catch (err) {
    console.error('❌ Interaction error:', err);
    if (!interaction.replied && !interaction.deferred) {
      await interaction.reply({
        content: '⚠️ Something went wrong while processing your request.',
        ephemeral: true
      });
    }
  }
}
});
client.on('guildMemberAdd', async (member) => {
  console.log(`${member.user.tag} joined ${member.guild.name}`);
  const welcomeChannelId = '1373078546422960148'; // Replace this
  const vouchesChannelId = '1373027974827212923'; // Replace this
  const proofsChannelId = '1373027988391596202';   // Replace this

  const welcomeChannel = member.guild.channels.cache.get(welcomeChannelId);
  if (!welcomeChannel) return;

  const embed = new EmbedBuilder()
    .setColor('#000000')
    .setThumbnail(member.user.displayAvatarURL({ dynamic: true }))
    .setDescription(
      `Welcome to **Azan’s Middleman Services** ${member}!\n\n` +
      `To view vouches: <#${vouchesChannelId}>\n` +
      `To view proofs: <#${proofsChannelId}>\n\n` +
      `We hope you enjoy your stay here!`
    )
    .setFooter({ text: `User ID: ${member.id}` })
    .setTimestamp();

  welcomeChannel.send({ embeds: [embed] }).catch(console.error);
});
app.get('/', (req, res) => {
  console.log('👀 UptimeRobot pinged the server');
  res.status(200).send('✅ Server is alive');
});
app.listen(3000, () => console.log('🌐 Express server is running'));

setInterval(() => {
  console.log('⏳ Self-ping running...');
  fetch('https://azan-s-mm-services.onrender.com/')
    .then(res => {
      console.log(`✅ Self-ping success: ${res.status} at ${new Date().toISOString()}`);
    })
    .catch(err => {
      console.error(`❌ Self-ping failed:`, err);
    });
}, 1000 * 60 * 5); // Every 5