import os
import datetime as dt
import discord
from discord.ext import commands
from utils.constants import BASE_URL, EMBED_COLOR, TRANSCRIPT_CHANNEL_ID
from utils.db import collections
import chat_exporter

def ensure_transcript_dir():
    path = os.path.join(os.getcwd(), "transcripts")
    os.makedirs(path, exist_ok=True)
    return path

class Transcripts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            # chat_exporter may optionally need initialization depending on version
            chat_exporter.init_exporter(bot)
        except Exception:
            # not fatal — keep going
            pass

    async def generate_transcript(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """
        Generate a transcript using chat-exporter, store HTML on disk (served via BASE_URL),
        attach only the TXT file and send the embed+link to both the user and the transcript log channel.
        """
        try:
            if not isinstance(channel, discord.TextChannel):
                return await interaction.response.send_message("❌ Not a text channel.", ephemeral=True)

            # Collect messages and participant stats
            msgs = [m async for m in channel.history(limit=None, oldest_first=True)]
            participants = {}
            for m in msgs:
                if not m.author.bot:
                    participants[m.author.id] = participants.get(m.author.id, 0) + 1

            # Generate HTML transcript via chat-exporter (returns HTML string)
            transcript_html = await chat_exporter.export(
                channel,
                limit=None,
                tz_info="UTC",
                military_time=True,
                bot=self.bot
            )

            if transcript_html is None:
                return await interaction.response.send_message("❌ Could not generate transcript.", ephemeral=True)

            folder = ensure_transcript_dir()
            html_name = f"{channel.id}.html"
            txt_name = f"transcript-{channel.id}.txt"

            # Save HTML on disk (so BASE_URL link can point to it)
            html_path = os.path.join(folder, html_name)
            try:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(transcript_html)
            except Exception as e:
                # log but continue (we can still provide the html string as link if your server serves it)
                print(f"❌ Failed to write HTML transcript to disk: {e}")

            # Save text version (attachable)
            txt_path = os.path.join(folder, txt_name)
            with open(txt_path, "w", encoding="utf-8") as f:
                for m in msgs:
                    ts = m.created_at.isoformat()
                    content = m.clean_content or (
                        "[Embed]" if m.embeds else "[Attachment]" if m.attachments else ""
                    )
                    f.write(f"[{ts}] {m.author}: {content}\n")

            # Save record in DB
            try:
                colls = await collections()
                if colls and colls.get("transcripts"):
                    await colls["transcripts"].insert_one({
                        "channelId": str(channel.id),
                        "channelName": channel.name,
                        "participants": [{"userId": str(uid), "count": c} for uid, c in participants.items()],
                        "createdAt": dt.datetime.utcnow(),
                    })
            except Exception as e:
                print(f"❌ Error saving transcript to DB: {e}")

            # HTML link served by your web server
            html_link = f"{BASE_URL}/transcripts/{html_name}"

            # Build the embed
            embed = discord.Embed(
                title="📄 Transcript Ready",
                description="Your ticket transcript is now ready.",
                color=EMBED_COLOR
            )
            embed.add_field(name="Ticket Name", value=channel.name, inline=True)
            embed.add_field(name="Ticket ID", value=str(channel.id), inline=True)
            p_text = "\n".join([f"<@{uid}> — `{cnt}` messages" for uid, cnt in participants.items()]) or "None"
            embed.add_field(name="Participants", value=p_text[:1024], inline=False)
            embed.set_footer(text="Transcript generated")

            # Add a link button to HTML (no HTML file is attached)
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="View HTML Transcript", style=discord.ButtonStyle.link, url=html_link))

            # Prepare the TXT file to attach
            txt_file = discord.File(txt_path, filename=txt_name)

            # Send to the user (ephemeral)
            try:
                if not getattr(interaction.response, "is_done", lambda: False)():
                    await interaction.response.send_message(embed=embed, view=view, files=[txt_file], ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, view=view, files=[txt_file], ephemeral=True)
            except Exception as e:
                print(f"❌ Error sending transcript to user: {e}")

            # Send to the transcript log channel (try cache then fetch)
            try:
                log_channel = None
                # guard: ensure TRANSCRIPT_CHANNEL_ID is valid
                if TRANSCRIPT_CHANNEL_ID:
                    try:
                        # try cached first
                        log_channel = self.bot.get_channel(int(TRANSCRIPT_CHANNEL_ID))
                    except Exception:
                        log_channel = None

                    if log_channel is None:
                        # try fetch (may raise)
                        try:
                            log_channel = await self.bot.fetch_channel(int(TRANSCRIPT_CHANNEL_ID))
                        except Exception:
                            log_channel = None

                if log_channel and isinstance(log_channel, discord.TextChannel):
                    # Re-create the file object (discord.File objects cannot be re-used after sending)
                    txt_file_for_log = discord.File(txt_path, filename=txt_name)
                    await log_channel.send(embed=embed, view=view, files=[txt_file_for_log])
                else:
                    print("❌ Transcript log channel not found or unavailable; skipping log send.")
            except Exception as e:
                print(f"❌ Could not send transcript to log channel: {e}")

        except Exception as e:
            # Fallback error reporting to interaction
            try:
                if not getattr(interaction.response, "is_done", lambda: False)():
                    await interaction.response.send_message(f"❌ Error generating transcript: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error generating transcript: {e}", ephemeral=True)
            except Exception:
                pass
            print(f"❌ Generate transcript failed: {e}")

    # ---------------------------
    # Button interaction
    # ---------------------------
    async def button_transcript(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.generate_transcript(interaction, channel)

    # ---------------------------
    # Command to generate transcript
    # ---------------------------
    @commands.command(name="transcript", help="Generates a transcript for this ticket.")
    async def transcript_cmd(self, ctx: commands.Context):
        if not isinstance(ctx.channel, discord.TextChannel):
            return await ctx.send("❌ This command can only be used in text channels.")

        class SimpleInteraction:
            def __init__(self, ctx):
                self.ctx = ctx
                self.response = self
            async def send_message(self, **kwargs):
                return await self.ctx.send(**kwargs)
            async def defer(self, **kwargs):
                pass
            async def followup(self, **kwargs):
                return await self.ctx.send(**kwargs)
            def is_done(self):
                return False

        await self.generate_transcript(SimpleInteraction(ctx), ctx.channel)

async def setup(bot):
    await bot.add_cog(Transcripts(bot))