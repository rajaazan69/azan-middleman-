import re
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from io import BytesIO
import aiohttp
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from utils.constants import (
    EMBED_COLOR, TICKET_CATEGORY_ID, MIDDLEMAN_ROLE_ID, OWNER_ID,
    LB_CHANNEL_ID, LB_MESSAGE_ID
)
from utils.db import collections

# ------------------------- Delete Button -------------------------
class DeleteTicketView(View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="Delete Ticket", style=discord.ButtonStyle.danger, custom_id="delete_ticket")
    async def delete_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id == self.owner_id or any(r.id == MIDDLEMAN_ROLE_ID for r in interaction.user.roles):
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ You don’t have permission to delete this ticket.", ephemeral=True)

# ------------------------- Trade Image Generator -------------------------
async def generate_trade_image(user1, user2, side1, side2, count1, count2, trade_desc):
    width, height = 600, 250
    card = Image.new("RGB", (width, height), (24, 26, 27))  # dark bg
    draw = ImageDraw.Draw(card)

    # Font paths
    BASE_DIR = Path(__file__).resolve().parent.parent  # go up from /cogs to project root
    FONT_PATH = BASE_DIR / "ARIAL.TTF"  # use your font file

    # Fonts
    font_big = ImageFont.truetype(str(FONT_PATH), 32)
    font_small = ImageFont.truetype(str(FONT_PATH), 22)

    # Title
    draw.text((width // 2, 20), "• TRADE •", font=font_big, fill=(255, 165, 0), anchor="mm")

    # Divider line
    draw.line([(20, 55), (580, 55)], fill=(70, 70, 70), width=2)

    # Fetch avatars
    async with aiohttp.ClientSession() as session:
        async with session.get(user1.display_avatar.url) as resp:
            avatar1 = Image.open(BytesIO(await resp.read())).convert("RGB").resize((64, 64))
        if user2:
            async with session.get(user2.display_avatar.url) as resp:
                avatar2 = Image.open(BytesIO(await resp.read())).convert("RGB").resize((64, 64))
        else:
            avatar2 = Image.new("RGB", (64, 64), (100, 100, 100))

    # User1 side
    draw.text((30, 70), f"[{count1}] {user1.display_name}'s side:", font=font_small, fill=(200, 200, 200))
    draw.text((30, 100), side1, font=font_small, fill=(255, 255, 255))
    card.paste(avatar1, (500, 60))

    # Divider
    draw.line([(20, 140), (580, 140)], fill=(70, 70, 70), width=2)

    # User2 side
    if user2:
        draw.text((30, 160), f"[{count2}] {user2.display_name}'s side:", font=font_small, fill=(200, 200, 200))
    else:
        draw.text((30, 160), f"[0] Unknown's side:", font=font_small, fill=(200, 200, 200))
    draw.text((30, 190), side2, font=font_small, fill=(255, 255, 255))
    card.paste(avatar2, (500, 160))

    # Save to buffer
    buffer = BytesIO()
    card.save(buffer, "PNG")
    buffer.seek(0)
    return buffer

# ------------------------- Send Trade Embed -------------------------
async def send_trade_embed(ticket_channel, user1, user2, side1, side2, trade_desc):
    colls = await collections()
    # Fetch ticket counts
    count1 = await colls["tickets"].count_documents({"user_id": str(user1.id)})
    count2 = await colls["tickets"].count_documents({"user_id": str(user2.id)}) if user2 else 0

    # Generate image
    image_bytes = await generate_trade_image(user1, user2, side1, side2, count1, count2, trade_desc)
    file = discord.File(fp=image_bytes, filename="trade.png")

    # Create embed
    embed = discord.Embed(color=0x2B2D31)
    embed.set_image(url="attachment://trade.png")
    embed.set_footer(text="Please wait for Middleman assistance")

    # Send with Delete button and ping line
    await ticket_channel.send(
        content=f"<@{OWNER_ID}> <@&{MIDDLEMAN_ROLE_ID}>",
        embed=embed,
        file=file,
        view=DeleteTicketView(owner_id=user1.id)
    )

# ------------------------- Close Panel -------------------------
class ClosePanel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="TRANSCRIPT", style=discord.ButtonStyle.secondary, custom_id="ticket_transcript")
    async def transcript_btn(self, interaction: discord.Interaction, _):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=True)

            cog = interaction.client.get_cog("Transcripts")
            if not cog:
                return await interaction.followup.send("❌ Transcript system not loaded.", ephemeral=True)

            await cog.generate_transcript(interaction, interaction.channel)
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @discord.ui.button(label="DELETE", style=discord.ButtonStyle.danger, custom_id="ticket_delete")
    async def delete_btn(self, interaction: discord.Interaction, _):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
            await interaction.channel.delete()
        except Exception as e:
            print("Delete Button Error:", e)

    @discord.ui.button(label="LOG POINTS", style=discord.ButtonStyle.success, custom_id="ticket_log_points")
    async def log_points_btn(self, interaction: discord.Interaction, _):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)

            channel = interaction.channel
            guild = interaction.guild
            if not isinstance(channel, discord.TextChannel) or getattr(channel, "category_id", None) != TICKET_CATEGORY_ID:
                return await interaction.followup.send("❌ This button can only be used inside ticket channels.", ephemeral=True)

            colls = await collections()
            tickets_coll = colls["tickets"]
            points_coll = colls["clientPoints"]

            ticket_data = await tickets_coll.find_one({"channelId": str(channel.id)})
            if not ticket_data:
                return await interaction.followup.send("❌ Could not find ticket data.", ephemeral=True)

            user_ids = [uid for uid in [ticket_data.get("user1"), ticket_data.get("user2")] if uid]
            if not user_ids:
                return await interaction.followup.send("❌ No users to log points for.", ephemeral=True)

            for uid in user_ids:
                await points_coll.update_one({"userId": uid}, {"$inc": {"points": 1}}, upsert=True)

            # Leaderboard
            lb_channel = guild.get_channel(LB_CHANNEL_ID)
            if not lb_channel:
                return await interaction.followup.send("❌ Leaderboard channel not found.", ephemeral=True)

            lb_message = None
            try:
                lb_message = await lb_channel.fetch_message(LB_MESSAGE_ID)
            except Exception:
                embed = discord.Embed(
                    title="🏆 Top Clients This Month",
                    description="No data yet.",
                    color=0x2B2D31,
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text="Client Leaderboard")
                lb_message = await lb_channel.send(embed=embed)

            top_users = await points_coll.find().sort("points", -1).limit(10).to_list(length=10)
            leaderboard_text = "\n".join(
                f"**#{i+1}** <@{user['userId']}> — **{user['points']}** point{'s' if user['points'] != 1 else ''}"
                for i, user in enumerate(top_users)
            ) or "No data yet."

            embed = discord.Embed(
                title="🏆 Top Clients This Month",
                description=leaderboard_text,
                color=0x2B2D31,
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Client Leaderboard")
            await lb_message.edit(embed=embed)

            await interaction.followup.send(f"✅ Logged 1 point for <@{'>, <@'.join(user_ids)}>.", ephemeral=True)
        except Exception as e:
            print("Log Points Button Error:", e)
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Something went wrong: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Something went wrong: {e}", ephemeral=True)

# ------------------------- Ticket Panel & Modal -------------------------
class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Request Middleman", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        class TicketModal(Modal, title="Middleman Request"):
            q1 = TextInput(label="What's the trade?", required=True, max_length=200)
            q2 = TextInput(label="What's your side?", style=discord.TextStyle.long, required=True, max_length=500)
            q3 = TextInput(label="What's their side?", style=discord.TextStyle.long, required=True, max_length=500)
            q4 = TextInput(label="Their Discord ID?", required=False, max_length=20)

            async def on_submit(self, modal_interaction: discord.Interaction):
                await modal_interaction.response.defer(ephemeral=True, thinking=False)
                try:
                    colls = await collections()
                    cat = modal_interaction.guild.get_channel(TICKET_CATEGORY_ID)
                    if cat:
                        for ch in cat.channels:
                            ow = ch.overwrites_for(modal_interaction.user)
                            if ow.view_channel:
                                return await modal_interaction.followup.send(f"❌ You already have an open ticket: {ch.mention}", ephemeral=True)

                    q1v, q2v, q3v, q4v = str(self.q1), str(self.q2), str(self.q3), str(self.q4)
                    target_member = None
                    if q4v and re.fullmatch(r"\d{17,19}", q4v):
                        target_member = modal_interaction.guild.get_member(int(q4v))

                    overwrites = {
                        modal_interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        modal_interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                    }
                    owner = modal_interaction.guild.get_member(OWNER_ID)
                    if owner:
                        overwrites[owner] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
                    middle_role = modal_interaction.guild.get_role(MIDDLEMAN_ROLE_ID)
                    if middle_role:
                        overwrites[middle_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
                    if target_member:
                        overwrites[target_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

                    ticket = await modal_interaction.guild.create_text_channel(
                        name=f"ticket-{modal_interaction.user.name}",
                        category=cat,
                        overwrites=overwrites
                    )

                    await colls["tickets"].insert_one({
                        "channelId": str(ticket.id),
                        "user1": str(modal_interaction.user.id),
                        "user2": str(target_member.id) if target_member else None
                    })

                    # Send trade embed
                    await send_trade_embed(ticket, modal_interaction.user, target_member, q2v, q3v, q1v)
                    await modal_interaction.followup.send(f"✅ Ticket created: {ticket.mention}", ephemeral=True)

                except Exception as e:
                    await modal_interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

        await interaction.response.send_modal(TicketModal())

# ------------------------- Main Cog -------------------------
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_panel(self, ctx: commands.Context, channel: discord.TextChannel | None = None):
        target = channel or ctx.channel
        embed = discord.Embed(
            title="Azan’s Middleman Service",
            description=(
                "To request a middleman from this server\n"
                "click the `Request Middleman` button below.\n\n"
                "**How does a Middleman Work?**\n"
                "Example: Trade is Harvester (MM2) for Robux.\n"
                "1. Seller gives Harvester to middleman.\n"
                "2. Buyer pays seller robux (after middleman confirms receiving mm2).\n"
                "3. Middleman gives buyer Harvester (after seller received robux).\n\n"
                "**Important**\n"
                "• Troll tickets are not allowed. Once the trade is completed you must vouch your middleman in their respective servers.\n"
                "• If you have trouble getting a user's ID click [here](https://youtube.com/shorts/pMG8CuIADDs?feature=shared).\n"
                f"• Make sure to read <#{TICKET_CATEGORY_ID}> before making a ticket."
            ),
            color=EMBED_COLOR
        )
        await target.send(embed=embed, view=TicketPanelView())
        await ctx.reply("✅ Setup complete.", mention_author=False)

    @commands.command(name="close")
    async def close_ticket(self, ctx: commands.Context):
        ch = ctx.channel
        if not isinstance(ch, discord.TextChannel) or (ch.category_id != TICKET_CATEGORY_ID):
            return await ctx.reply("❌ You can only close ticket channels!", mention_author=False)

        ticket_owner_id = None
        for target, overwrite in ch.overwrites.items():
            if isinstance(target, discord.Member) and target.id not in {ctx.guild.id, MIDDLEMAN_ROLE_ID, OWNER_ID}:
                if overwrite.view_channel:
                    ticket_owner_id = target.id
                    try:
                        await ch.set_permissions(target, send_messages=False, view_channel=False)
                    except:
                        pass

        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description="Select an option below to generate the transcript or delete the ticket.",
            color=0x2B2D31
        )
        embed.add_field(name="Ticket Name", value=ch.name, inline=True)
        embed.add_field(name="Owner", value=f"<@{ticket_owner_id}>" if ticket_owner_id else "Unknown", inline=True)
        embed.set_footer(text=f"Closed by {ctx.author}")
        await ctx.send(embed=embed, view=ClosePanel())

# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(Tickets(bot))