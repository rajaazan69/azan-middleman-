import discord
from discord.ext import commands
from discord.ui import View, Button
from io import BytesIO
import aiohttp
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from utils.constants import EMBED_COLOR, MIDDLEMAN_ROLE_ID, OWNER_ID, TICKET_CATEGORY_ID, LB_CHANNEL_ID, LB_MESSAGE_ID
from utils.db import collections

# ------------------------- Ticket Panel View -------------------------
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Request Middleman", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        class TicketModal(discord.ui.Modal, title="Middleman Request"):
            q1 = discord.ui.TextInput(label="What's the trade?", required=True, max_length=200)
            q2 = discord.ui.TextInput(label="What's your side?", style=discord.TextStyle.long, required=True, max_length=500)
            q3 = discord.ui.TextInput(label="What's their side?", style=discord.TextStyle.long, required=True, max_length=500)
            q4 = discord.ui.TextInput(label="Their Discord ID?", required=False, max_length=20)

            async def on_submit(self, modal_interaction: discord.Interaction):
                await modal_interaction.response.send_message("✅ Ticket submitted!", ephemeral=True)
                # Your existing ticket creation logic goes here (generate trade embed, Pillow image, etc.)

        await interaction.response.send_modal(TicketModal())

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
    width, height = 800, 400
    bg_color = (18, 18, 18)
    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Fonts (make sure the .ttf files exist)
    title_font = ImageFont.truetype("arialbd.ttf", 40)
    user_font = ImageFont.truetype("arialbd.ttf", 30)
    side_font = ImageFont.truetype("arial.ttf", 28)
    desc_font = ImageFont.truetype("arial.ttf", 24)

    # Draw Title
    draw.text((width//2, 30), "• TRADE •", font=title_font, fill=(255, 165, 0), anchor="mm")

    # Fetch avatars
    async with aiohttp.ClientSession() as session:
        async with session.get(user1.display_avatar.url) as r:
            user1_bytes = BytesIO(await r.read())
        user2_url = user2.display_avatar.url if user2 else "https://cdn.discordapp.com/embed/avatars/1.png"
        async with session.get(user2_url) as r:
            user2_bytes = BytesIO(await r.read())

    avatar_size = 100
    avatar1 = Image.open(user1_bytes).convert("RGBA").resize((avatar_size, avatar_size))
    avatar2 = Image.open(user2_bytes).convert("RGBA").resize((avatar_size, avatar_size))

    # Paste avatars
    img.paste(avatar1, (150, 100), avatar1)
    img.paste(avatar2, (width - 250, 100), avatar2)

    # Draw usernames + ticket counts
    draw.text((150 + avatar_size + 20, 110), f"{user1.name} [{count1}]", font=user_font, fill=(255, 255, 255))
    if user2:
        draw.text((width - 250 + avatar_size + 20, 110), f"{user2.name} [{count2}]", font=user_font, fill=(255, 255, 255))
    else:
        draw.text((width - 250 + avatar_size + 20, 110), "Unknown User [0]", font=user_font, fill=(200, 200, 200))

    # Draw sides
    draw.text((150 + avatar_size + 20, 150), f"Side: {side1}", font=side_font, fill=(255, 255, 255))
    draw.text((width - 250 + avatar_size + 20, 150), f"Side: {side2}", font=side_font, fill=(255, 255, 255))

    # Draw trade description at bottom
    draw.text((width//2, 300), trade_desc, font=desc_font, fill=(255, 255, 255), anchor="mm")

    final_bytes = BytesIO()
    img.save(final_bytes, format="PNG")
    final_bytes.seek(0)
    return final_bytes

# ------------------------- Send Trade Embed -------------------------
async def send_trade_embed(ticket_channel, user1, user2, side1, side2, trade_desc):
    colls = await collections()
    count1 = await colls["tickets"].count_documents({"user_id": str(user1.id)})
    count2 = await colls["tickets"].count_documents({"user_id": str(user2.id)}) if user2 else 0

    image_bytes = await generate_trade_image(user1, user2, side1, side2, count1, count2, trade_desc)
    file = discord.File(fp=image_bytes, filename="trade.png")

    embed = discord.Embed(title="• TRADE •", color=0x000000)
    embed.set_image(url="attachment://trade.png")
    embed.set_footer(text="Please wait for Middleman assistance")

    await ticket_channel.send(
        content=f"<@{OWNER_ID}> <@&{MIDDLEMAN_ROLE_ID}>",
        embed=embed,
        file=file,
        view=DeleteTicketView(owner_id=user1.id)
    )

# ------------------------- Close ticket view -------------------------
class ClosePanel(discord.ui.View):
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
            print("Transcript Button Error:", e)

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
            lb_channel = guild.get_channel(LB_CHANNEL_ID)
            if not lb_channel:
                return await interaction.followup.send("❌ Leaderboard channel not found.", ephemeral=True)
            lb_message = None
            try:
                lb_message = await lb_channel.fetch_message(LB_MESSAGE_ID)
            except Exception:
                embed = discord.Embed(title="🏆 Top Clients This Month", description="No data yet.", color=0x2B2D31, timestamp=datetime.utcnow())
                embed.set_footer(text="Client Leaderboard")
                lb_message = await lb_channel.send(embed=embed)
            top_users = await points_coll.find().sort("points", -1).limit(10).to_list(length=10)
            leaderboard_text = "\n".join(
                f"**#{i+1}** <@{user['userId']}> — **{user['points']}** point{'s' if user['points'] != 1 else ''}" for i, user in enumerate(top_users)
            ) or "No data yet."
            embed = discord.Embed(title="🏆 Top Clients This Month", description=leaderboard_text, color=0x2B2D31, timestamp=datetime.utcnow())
            embed.set_footer(text="Client Leaderboard")
            await lb_message.edit(embed=embed)
            await interaction.followup.send(f"✅ Logged 1 point for <@{'>, <@'.join(user_ids)}>.", ephemeral=True)
        except Exception as e:
            print("Log Points Button Error:", e)

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

# ------------------------- Cog setup -------------------------
async def setup(bot):
    await bot.add_cog(Tickets(bot))