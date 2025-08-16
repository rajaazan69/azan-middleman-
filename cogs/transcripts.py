import os
import html
import datetime as dt
import discord
from discord.ext import commands
from utils.constants import BASE_URL, EMBED_COLOR, TRANSCRIPT_CHANNEL_ID, LEADERBOARD_CHANNEL_ID, LEADERBOARD_MESSAGE_ID
from utils.db import collections

def ensure_transcript_dir():
    path = os.path.join(os.getcwd(), "transcripts")
    os.makedirs(path, exist_ok=True)
    return path

def render_html(channel: discord.TextChannel, messages: list[discord.Message]) -> bytes:
    # simple clean HTML similar to discord transcript feel
    lines = []
    for m in messages:
        ts = dt.datetime.fromtimestamp(m.created_at.timestamp()).isoformat()
        author = html.escape(f"{m.author} ({m.author.id})")
        content = html.escape(m.clean_content) if m.content else ""
        if not content:
            if m.embeds:
                content = "[Embed]"
            elif m.attachments:
                content = "[Attachment]"
            else:
                content = ""
        lines.append(f"<div><span style='opacity:.6'>[{ts}]</span> <b>{author}</b>: {content}</div>")
    body = "\n".join(lines)
    html_doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{html.escape(channel.name)}</title>
<style>body{{font-family:system-ui,Segoe UI,Arial,sans-serif;background:#2b2d31;color:#e3e5e8;}}
div{{padding:6px 8px;border-bottom:1px solid #373a3f}}</style></head>
<body><h2>Transcript — {html.escape(channel.name)}</h2>{body}</body></html>"""
    return html_doc.encode("utf-8")

class Transcripts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def generate_transcript(self, interaction: discord.Interaction, channel: discord.abc.Messageable):
        if not isinstance(channel, discord.TextChannel):
            return await interaction.edit_original_response(content="❌ Not a text channel.")
        await channel.trigger_typing()

        msgs = [m async for m in channel.history(limit=None, oldest_first=True)]
        participants = {}
        for m in msgs:
            if not m.author.bot:
                participants[m.author.id] = participants.get(m.author.id, 0) + 1

        folder = ensure_transcript_dir()
        html_bytes = render_html(channel, msgs)
        html_name = f"{channel.id}.html"
        txt_name = f"transcript-{channel.id}.txt"

        with open(os.path.join(folder, html_name), "wb") as f:
            f.write(html_bytes)

        with open(os.path.join(folder, txt_name), "w", encoding="utf-8") as f:
            for m in msgs:
                ts = m.created_at.isoformat()
                content = m.clean_content or ("[Embed]" if m.embeds else "[Attachment]" if m.attachments else "")
                f.write(f"[{ts}] {m.author}: {content}\n")

        colls = await collections()
        await colls["transcripts"].insert_one({
            "channelId": str(channel.id),
            "channelName": channel.name,
            "participants": [{"userId": str(uid), "count": c} for uid, c in participants.items()],
            "createdAt": dt.datetime.utcnow(),
        })

        html_link = f"{BASE_URL}/transcripts/{html_name}"

        embed = discord.Embed(title="📄 Transcript Ready", description="Your ticket transcript is now ready.", color=EMBED_COLOR)
        embed.add_field(name="Ticket Name", value=channel.name, inline=True)
        embed.add_field(name="Ticket ID", value=str(channel.id), inline=True)
        p_text = "\n".join([f"<@{uid}> — `{cnt}` messages" for uid, cnt in participants.items()]) or "None"
        embed.add_field(name="Participants", value=p_text[:1024], inline=False)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="View HTML Transcript", style=discord.ButtonStyle.link, url=html_link))

        await interaction.edit_original_response(embed=embed, view=view, attachments=[discord.File(os.path.join(folder, txt_name))])

        log = self.bot.get_channel(TRANSCRIPT_CHANNEL_ID)
        if isinstance(log, discord.TextChannel):
            await log.send(embed=embed, view=view, file=discord.File(os.path.join(folder, txt_name)))

    async def log_points(self, interaction: discord.Interaction):
        colls = await collections()
        ch = interaction.channel
        if not isinstance(ch, discord.TextChannel):
            return await interaction.edit_original_response(content="❌ Not a ticket channel.")

        ticket = await colls["tickets"].find_one({"channelId": str(ch.id)})
        if not ticket:
            return await interaction.edit_original_response(content="❌ Could not find ticket data.")

        for uid in [ticket.get("user1"), ticket.get("user2")]:
            if not uid:
                continue
            await colls["clientPoints"].update_one({"userId": uid}, {"$inc": {"points": 1}}, upsert=True)

        if LEADERBOARD_CHANNEL_ID and LEADERBOARD_MESSAGE_ID:
            lb_ch = self.bot.get_channel(LEADERBOARD_CHANNEL_ID)
            try:
                msg = await lb_ch.fetch_message(LEADERBOARD_MESSAGE_ID)  # type: ignore
                top = colls["clientPoints"].find().sort("points", -1).limit(10)
                lines = []
                rank = 1
                async for user in top:
                    lines.append(f"**#{rank}** <@{user['userId']}> — **{user['points']}** point{'s' if user['points']!=1 else ''}")
                    rank += 1
                embed = discord.Embed(title="🏆 Top Clients This Month", description="\n".join(lines) or "No data yet.", color=0x2B2D31)
                await msg.edit(embed=embed)
            except Exception:
                pass

        await interaction.edit_original_response(content="✅ Logged 1 point for ticket users.")

async def setup(bot):
    await bot.add_cog(Transcripts(bot))