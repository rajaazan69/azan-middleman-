import re
import io
import math
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from io import BytesIO
import aiohttp
from datetime import datetime
from utils.constants import (
    EMBED_COLOR, TICKET_CATEGORY_ID, MIDDLEMAN_ROLE_ID, OWNER_ID,
    LB_CHANNEL_ID, LB_MESSAGE_ID
)
from utils.db import collections
from PIL import Image, ImageDraw, ImageFont

# ====== CONFIG: your one-time Cloudinary base template ======
CLOUDINARY_TEMPLATE_URL = "https://res.cloudinary.com/ddvgelgbg/image/upload/v1755638544/E9AADBCB-0F63-4CF6-A025-2EAF96945B9C_lltnoa.png"

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

# ------------------------- Helper: fonts -------------------------
def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    Try common fonts; fall back to PIL default so we never error.
    """
    for name in ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "Arial.ttf"]:
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()

# ------------------------- Helper: text utils -------------------------
def _truncate_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_w: int) -> str:
    """
    Keep as much text as fits; add ellipsis if needed.
    """
    if draw.textlength(text, font=font) <= max_w:
        return text
    ell = "…"
    if draw.textlength(ell, font=font) > max_w:
        return ""
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi) // 2
        t = text[:mid] + ell
        if draw.textlength(t, font=font) <= max_w:
            lo = mid + 1
        else:
            hi = mid
    return text[:max(0, lo - 1)] + ell

# ------------------------- Helper: fetch & prepare images -------------------------
async def _fetch_bytes(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.read()

def _square_fit(im: Image.Image, size: int) -> Image.Image:
    """
    Center-crop to square, then resize to (size, size).
    """
    w, h = im.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    im = im.crop((left, top, left + side, top + side))
    return im.resize((size, size), Image.LANCZOS)

# ------------------------- Trade Image Generator (Template + PIL) -------------------------
async def generate_trade_image(user1, user2, side1, side2, count1, count2):
    """
    Uses your Cloudinary template as background; overlays:
      [count] @user1 side:
      their side: <value>
      [count] @user2 side:
      their side: <value>     [avatar2 aligned to this line]
    Avatars are SQUARE, hard-coded positions to match template.
    """
    # 1) Load base template
    template_bytes = await _fetch_bytes(CLOUDINARY_TEMPLATE_URL)
    base = Image.open(BytesIO(template_bytes)).convert("RGBA")
    W, H = base.size

    # 2) Compute hard-coded layout (relative to template size)
    # Margins & avatar sizing
    margin_x = int(W * 0.055)           # left padding for text
    right_margin = int(W * 0.055)       # right padding
    avatar_size = int(H * 0.20)         # square avatar size
    gap_y = int(H * 0.035)              # vertical gap between blocks

    # Title is already baked into template; we position beneath the first divider area.
    # Choose y-anchors for two blocks that match your screenshot proportions:
    block1_top = int(H * 0.27)          # top of user1 name line
    block2_top = int(H * 0.59)          # top of user2 name line

    # Text fonts (scale with canvas height)
    name_size = max(22, int(H * 0.055))        # for "[count] @user side:"
    side_size = max(20, int(H * 0.045))        # for "their side: ..."
    font_name = _load_font(name_size)
    font_side = _load_font(side_size)

    # Avatar X positions (right aligned)
    avatar_x = W - right_margin - avatar_size

    # 3) Load avatars (square)
    # user1 avatar aligned with the *name* line
    a1_bytes = await _fetch_bytes(user1.display_avatar.with_static_format("png").url)
    a1 = Image.open(BytesIO(a1_bytes)).convert("RGBA")
    a1 = _square_fit(a1, avatar_size)

    # user2 may be None
    a2 = None
    if user2:
        a2_bytes = await _fetch_bytes(user2.display_avatar.with_static_format("png").url)
        a2 = Image.open(BytesIO(a2_bytes)).convert("RGBA")
        a2 = _square_fit(a2, avatar_size)

    # 4) Draw text
    draw = ImageDraw.Draw(base)

    # Safe area width for text (so it doesn't collide with avatar)
    max_text_w = avatar_x - margin_x - int(W * 0.02)

    # -------- Block 1 (User1) --------
    line1_text = f"[{count1}] @{user1.display_name} side:"
    line1_text = _truncate_to_width(draw, line1_text, font_name, max_text_w)
    draw.text((margin_x, block1_top), line1_text, fill="white", font=font_name)

    side1_text = f"their side: {side1}"
    side1_text = _truncate_to_width(draw, side1_text, font_side, max_text_w)
    side1_y = block1_top + int(name_size * 1.25)
    draw.text((margin_x, side1_y), side1_text, fill=(220, 220, 220, 255), font=font_side)

    # Avatar1 aligned to name line
    base.alpha_composite(a1, (avatar_x, block1_top))

    # -------- Block 2 (User2) --------
    # Name line
    if user2:
        line2_text = f"[{count2}] @{user2.display_name} side:"
    else:
        line2_text = f"[{count2}] @Unknown side:"
    line2_text = _truncate_to_width(draw, line2_text, font_name, max_text_w)
    draw.text((margin_x, block2_top), line2_text, fill="white", font=font_name)

    # Side line (avatar aligned to this side line for user2)
    side2_text = f"their side: {side2}"
    side2_text = _truncate_to_width(draw, side2_text, font_side, max_text_w)
    side2_y = block2_top + int(name_size * 1.25)
    draw.text((margin_x, side2_y), side2_text, fill=(220, 220, 220, 255), font=font_side)

    if a2:
        # Align avatar to the SIDE line (as you requested)
        base.alpha_composite(a2, (avatar_x, side2_y))

    # 5) Export to bytes
    out = BytesIO()
    base.save(out, format="PNG")
    out.seek(0)
    return out

# ------------------------- Send Trade Embed -------------------------
async def send_trade_embed(ticket_channel, user1, user2, side1, side2, trade_desc):
    colls = await collections()
    tickets_coll = colls["tickets"]

    # Count appearances where user is either user1 or user2 in your tickets collection
    async def _count_user(uid: int) -> int:
        return await tickets_coll.count_documents({"$or": [{"user1": str(uid)}, {"user2": str(uid)}]})

    count1 = await _count_user(user1.id)
    count2 = await _count_user(user2.id) if user2 else 0

    image_bytes = await generate_trade_image(user1, user2, side1, side2, count1, count2)
    file = discord.File(fp=image_bytes, filename="trade.png")

    # Match Discord dark embed look
    embed = discord.Embed(color=0x2F3136)
    embed.set_image(url="attachment://trade.png")
    embed.set_footer(text=f"Trade: {trade_desc}")

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