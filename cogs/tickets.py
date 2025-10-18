import re
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from datetime import datetime
from utils.constants import (
    EMBED_COLOR, TICKET_CATEGORY_ID, MIDDLEMAN_ROLE_ID, OWNER_ID,
    LB_CHANNEL_ID, LB_MESSAGE_ID
)
from utils.db import collections
from .crypto_buttons import CryptoButtonView
from utils.ticket_stats import increment_ticket_count, get_ticket_count

# ------------------------- Helpers -------------------------
PLACEHOLDER_AVATAR = "https://cdn.discordapp.com/embed/avatars/0.png"

def _avatar_url(user: discord.abc.User, size: int = 1024) -> str:
    try:
        return user.display_avatar.replace(size=size, format="png").url
    except Exception:
        try:
            return user.display_avatar.with_static_format("png").url
        except Exception:
            return getattr(user, "avatar_url", PLACEHOLDER_AVATAR)

async def _count_user_tickets(uid: int) -> int:
    colls = await collections()
    tickets_coll = colls["tickets"]
    uid_str = str(uid)

    count = await tickets_coll.count_documents({
        "$or": [
            {"user1": uid_str},
            {"user2": uid_str}
        ]
    })
    return count
# ------------------------- Delete View -------------------------
class DeleteTicketView(View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(
        label="Delete Ticket",
        style=discord.ButtonStyle.danger,
        emoji="<a:redcrossanimated:1103550228424032277>",
        custom_id="delete_ticket"
    )
    async def delete_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id == self.owner_id or any(r.id == MIDDLEMAN_ROLE_ID for r in interaction.user.roles):
            try:
                await interaction.response.defer()
            except Exception:
                pass
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ You don't have permission to delete this ticket.", ephemeral=True)

# ------------------------- Claim + Delete View -------------------------
class ClaimAndDeleteView(View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="🔐 Claim", style=discord.ButtonStyle.success, custom_id="ticket_claim")
    async def claim_button(self, interaction: discord.Interaction, button: Button):
        member = interaction.user
        guild = interaction.guild
        ch = interaction.channel

        if not any(r.id == MIDDLEMAN_ROLE_ID for r in member.roles):
            return await interaction.response.send_message("❌ Only middlemen can claim tickets.", ephemeral=True)

        colls = await collections()
        tickets_coll = colls["tickets"]
        ticket_doc = await tickets_coll.find_one({"channelId": str(ch.id)})
        if ticket_doc and ticket_doc.get("claimedBy"):
            return await interaction.response.send_message("❌ This ticket is already claimed.", ephemeral=True)

        try:
            await interaction.response.defer()
        except Exception:
            pass

        mm_role = guild.get_role(MIDDLEMAN_ROLE_ID)
        if mm_role:
            try:
                await ch.set_permissions(mm_role, send_messages=False, view_channel=True)
            except Exception:
                pass

        try:
            await ch.set_permissions(member, send_messages=True, view_channel=True)
        except Exception:
            pass

        try:
            await ch.edit(name=f"ticket-{member.name}")
        except Exception:
            try:
                await ch.edit(name=f"ticket-{member.display_name}")
            except Exception:
                pass

        await tickets_coll.update_one(
            {"channelId": str(ch.id)},
            {"$set": {"claimedBy": str(member.id)}},
            upsert=True
        )

        try:
            await ch.send(f"{member.mention} will be your middleman for this trade.")
        except Exception:
            pass

        try:
            mm_coll = colls["middlemen"]
            data = await mm_coll.find_one({"_id": member.id})
            completed = int(data.get("completed", 0)) if data else 0
        except Exception:
            completed = 0

        profile = discord.Embed(
            title="__**• Middleman Profile •**__",
            color=0x000000
        )
        try:
            profile.set_thumbnail(url=member.display_avatar.url)
        except Exception:
            profile.set_thumbnail(url=PLACEHOLDER_AVATAR)

        profile.description = (
            f"**| Username:** {member.mention} (`{member}`)\n"
            f"**| User ID:** `{member.id}`\n"
            f"**| Account Created:** {member.created_at.strftime('%B %d, %Y')}\n"
            f"**| Completed Tickets:** **{completed}**"
        )

        try:
            await ch.send(embed=profile, view=ClaimView(member.id))
        except Exception:
            pass

        try:
            if interaction.message:
                await interaction.message.edit(view=DeleteTicketView(owner_id=self.owner_id))
        except Exception:
            pass

# ------------------------- Claim View (W Button) -------------------------
import discord
from utils.db import collections
from .crypto_buttons import get_crypto_address  # Use your crypto function directly

class ClaimView(discord.ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=None)
        self.member_id = member_id

        # --- W Button ---
        w_btn = discord.ui.Button(label="w", style=discord.ButtonStyle.secondary, custom_id="ticket_w")
        w_btn.callback = self.w_button_callback
        self.add_item(w_btn)

        # --- LTC Button ---
        ltc_btn = discord.ui.Button(label="LTC", style=discord.ButtonStyle.primary,
                                    emoji="<:emoji_27:1413667063951659038>", custom_id="ticket_ltc")
        ltc_btn.callback = self.ltc_callback
        self.add_item(ltc_btn)

        # --- ETH Button ---
        eth_btn = discord.ui.Button(label="ETH", style=discord.ButtonStyle.primary,
                                    emoji="<:emoji_26:1413666923756912640>", custom_id="ticket_eth")
        eth_btn.callback = self.eth_callback
        self.add_item(eth_btn)

    # ---------------- W Button ----------------
    async def w_button_callback(self, interaction: discord.Interaction):
        allowed_role_id = 1373029428409405500
        has_role = any(r.id == allowed_role_id for r in interaction.user.roles)
        is_admin = interaction.user.guild_permissions.administrator

        if not (has_role or is_admin):
            return await interaction.response.send_message(
                "❌ You don’t have permission to use this button.", ephemeral=True
            )

        ch = interaction.channel

        colls = await collections()
        users_coll = colls["tags"]
        tickets_coll = colls["tickets"]

        ticket_doc = await tickets_coll.find_one({"channelId": str(ch.id)})
        mm_id = ticket_doc.get("claimedBy") if ticket_doc else None

        if not mm_id:
            return await interaction.response.send_message(
                "❌ Could not find the middleman for this ticket.", ephemeral=True
            )

        user_doc = await users_coll.find_one({"_id": str(mm_id)})
        if not user_doc:
            return await interaction.response.send_message(
                "❌ No Roblox user saved for this middleman.", ephemeral=True
            )

        query = user_doc.get("robloxUser")
        if not query:
            return await interaction.response.send_message(
                "❌ No Roblox username found for this middleman.", ephemeral=True
            )

        import aiohttp
        roblox_data = None
        thumb_url = "https://www.roblox.com/images/logo/roblox_logo_300x300.png"

        async with aiohttp.ClientSession() as session:
            if not query.isdigit():
                async with session.post(
                    "https://users.roblox.com/v1/usernames/users",
                    json={"usernames": [query], "excludeBannedUsers": False}
                ) as resp:
                    data = await resp.json()
                    if data["data"]:
                        roblox_id = data["data"][0]["id"]
                    else:
                        return await interaction.response.send_message(
                            f"❌ Could not find Roblox user `{query}`.", ephemeral=True
                        )
            else:
                roblox_id = int(query)

            async with session.get(f"https://users.roblox.com/v1/users/{roblox_id}") as resp:
                roblox_data = await resp.json()

            async with session.get(
                f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={roblox_id}&size=150x150&format=Png&isCircular=false"
            ) as resp:
                thumb_data = await resp.json()
                if thumb_data["data"]:
                    thumb_url = thumb_data["data"][0]["imageUrl"]

        profile_link = f"https://www.roblox.com/users/{roblox_id}/profile"

        embed = discord.Embed(
            color=0x000000 if not roblox_data.get("isBanned") else 0xFF0000
        )
        embed.set_author(name=roblox_data["name"], icon_url=thumb_url, url=profile_link)
        embed.set_thumbnail(url=thumb_url)
        embed.add_field(name="Display Name", value=f"`{roblox_data['displayName']}`")
        embed.add_field(name="ID", value=f"`{roblox_data['id']}`")
        embed.add_field(name="Created", value=roblox_data["created"])
        if roblox_data.get("description"):
            embed.add_field(name="Description", value=roblox_data["description"][:1020], inline=False)
        if roblox_data.get("isBanned"):
            embed.add_field(name="Status", value="BANNED")

        row = discord.ui.View()
        row.add_item(discord.ui.Button(label="Profile Link", style=discord.ButtonStyle.link, url=profile_link))
        await interaction.response.send_message(embed=embed, view=row)

    # ---------------- LTC Button ----------------
    async def ltc_callback(self, interaction: discord.Interaction):
        allowed_role_id = 1373029428409405500
        has_role = any(r.id == allowed_role_id for r in interaction.user.roles)
        is_admin = interaction.user.guild_permissions.administrator

        if not (has_role or is_admin):
            return await interaction.response.send_message(
                "❌ You don’t have permission to use this button.", ephemeral=True
            )
        address = get_crypto_address(str(self.member_id), "LTC")
        if not address:
            return await interaction.response.send_message("❌ No LTC address saved for this middleman.", ephemeral=True)

        embed = discord.Embed(
            title="__**• LTC Address •**__",
            description=f"**Address:**\n`{address}`\n\n**⚠️ Warning:** *Funds sent to the wrong address will be lost!*",
            color=0x000000
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1373070247795495116/1413678740181094420/IMG_9236.jpg?ex=68bcce6c&is=68bb7cec&hm=7a86021930670dac0b5768c8fac5604a66737ede8319d6a32bb516ec675e5ab6&")
        await interaction.response.send_message(embed=embed)

    # ---------------- ETH Button ----------------
    async def eth_callback(self, interaction: discord.Interaction):
        allowed_role_id = 1373029428409405500
        has_role = any(r.id == allowed_role_id for r in interaction.user.roles)
        is_admin = interaction.user.guild_permissions.administrator

        if not (has_role or is_admin):
            return await interaction.response.send_message(
                "❌ You don’t have permission to use this button.", ephemeral=True
            )
        address = get_crypto_address(str(self.member_id), "ETH")
        if not address:
            return await interaction.response.send_message("❌ No ETH address saved for this middleman.", ephemeral=True)

        embed = discord.Embed(
            title="__**• ETH Address •**__",
            description=f"**Address:**\n`{address}`\n\n**⚠️ Warning:** *Funds sent to the wrong address will be lost!*",
            color=0x000000
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1373070247795495116/1413678763711004672/IMG_9237.jpg?ex=68bcce72&is=68bb7cf2&hm=f9cdcc13495c2d778fa8141bc48fef5b538a659617cda2f3f3e2c2074a862ad9&")
        await interaction.response.send_message(embed=embed)
# ------------------------- Trade Embeds -------------------------
async def send_trade_embed(ticket_channel, user1, user2, side1, side2, trade_desc):
    count1 = get_ticket_count(user1.id)
    count2 = get_ticket_count(user2.id) if user2 else 0
    
    avatar1 = _avatar_url(user1) if user1 else PLACEHOLDER_AVATAR
    avatar2 = _avatar_url(user2) if user2 else PLACEHOLDER_AVATAR

    mention1 = user1.mention if user1 else "Unknown User"
    mention2 = user2.mention if user2 else "`(no user provided)`"

    embed1 = discord.Embed(
        title="__**• Trade •**__" if trade_desc else None,
        description=f"| **[{count1}] {mention1} side:**\n| **{side1 or '(not provided)'}**",
        color=0x000000
    )
    embed1.set_thumbnail(url=avatar1)

    embed2 = discord.Embed(
        description=f"\u200b| **[{count2}] {mention2} side:**\n| **{side2 or '(not provided)'}**",
        color=0x000000
    )
    embed2.set_thumbnail(url=avatar2)

    await ticket_channel.send(
        content=(
            f"**{mention1}** has created a ticket with **{mention2}**.\n"
            "A middleman will be with you shortly.\n"
            f"||<@&{MIDDLEMAN_ROLE_ID}> <@{OWNER_ID}>||"
        ),
        embeds=[embed1, embed2],
        view=ClaimAndDeleteView(owner_id=user1.id)
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
            allowed = (
                any(r.id == MIDDLEMAN_ROLE_ID for r in interaction.user.roles)
                or interaction.user.guild_permissions.administrator
            )
            if not allowed:
                return await interaction.response.send_message(
                    "❌ You don't have permission to delete this ticket.", ephemeral=True
                )

            if not interaction.response.is_done():
                await interaction.response.defer()
            await interaction.channel.delete()
        except Exception as e:
            print("Delete Button Error:", e)
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @discord.ui.button(label="LOG POINTS", style=discord.ButtonStyle.success, custom_id="ticket_log_points")
    async def log_points_btn(self, interaction: discord.Interaction, _):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
    
            channel = interaction.channel
            colls = await collections()
            tickets_coll = colls["tickets"]
            points_coll = colls["clientPoints"]
    
            ticket_data = await tickets_coll.find_one({"channelId": str(channel.id)})
            if not ticket_data:
                return await interaction.followup.send("❌ Could not find ticket data.", ephemeral=True)
    
            # ensure user IDs are strings
            user_ids = [str(uid) for uid in [ticket_data.get("user1"), ticket_data.get("user2")] if uid]
            if not user_ids:
                return await interaction.followup.send("❌ No users to log points for.", ephemeral=True)
    
            # increment points (no points in $setOnInsert)
            for uid in user_ids:
                await points_coll.update_one(
                    {"userId": uid},
                    {"$inc": {"points": 1}, "$setOnInsert": {"userId": uid}},
                    upsert=True
                )
    
            # Update leaderboard (safe .get usage)
            lb_channel = interaction.guild.get_channel(LB_CHANNEL_ID)
            if lb_channel:
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
                    f"**#{i+1}** <@{user.get('userId')}> — **{user.get('points', 0)}** point{'s' if user.get('points', 0) != 1 else ''}"
                    for i, user in enumerate(top_users)
                    if user.get("userId")
                ) or "No data yet."
    
                embed = discord.Embed(
                    title="🏆 Top Clients This Month",
                    description=leaderboard_text,
                    color=0x2B2D31,
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text="Client Leaderboard")
                await lb_message.edit(embed=embed)
    
            mentions = ", ".join(f"<@{uid}>" for uid in user_ids)
            await interaction.followup.send(f"✅ Logged 1 point for {mentions}.", ephemeral=True)
    
        except Exception as e:
            print("Log Points Button Error:", e)
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Something went wrong: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Something went wrong: {e}", ephemeral=True)
# ------------------------- Ticket Panel & Modal -------------------------
MM_BANNED_ROLE_ID = 1395343230832349194  # 🔒 MM Banned role

class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Request Middleman", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        class TicketModal(Modal, title="Middleman Request"):
            q1 = TextInput(label="What's the trade?",placeholder="Describe the full trade e.g gag for sab",required=True, max_length=200)
            q2 = TextInput(label="What's your side?",placeholder="Describe your side e.g gag",style=discord.TextStyle.long, required=True, max_length=500)
            q3 = TextInput(label="What's their side?",placeholder="Describe the other traders side e.g sab",style=discord.TextStyle.long, required=True, max_length=500)
            q4 = TextInput(label="Their Discord ID?",placeholder="The other traders user ID",required=False, max_length=20)

            async def on_submit(self, modal_interaction: discord.Interaction):

                # 🔒 MM BANNED CHECK HERE (before deferring)
                if any(r.id == MM_BANNED_ROLE_ID for r in modal_interaction.user.roles):
                    embed = discord.Embed(
                        title="❌ Unable to Create Ticket",
                        description=(
                            "You are currently **MM Banned** and cannot create tickets.\n\n"
                            "**Reason:** `Middleman Ban`\n"
                            "Please ping an **admin** to resolve this."
                        ),
                        color=EMBED_COLOR
                    )
                    return await modal_interaction.response.send_message(embed=embed, ephemeral=True)

                # ✅ Passed MM Ban check
                await modal_interaction.response.defer(ephemeral=True)

                try:
                    colls = await collections()
                    cat = modal_interaction.guild.get_channel(TICKET_CATEGORY_ID)
                    if cat:
                        for ch in cat.channels:
                            ow = ch.overwrites_for(modal_interaction.user)
                            if ow.view_channel:
                                return await modal_interaction.followup.send(
                                    f"❌ You already have an open ticket: {ch.mention}", ephemeral=True
                                )

                    q1v, q2v, q3v, q4v = str(self.q1), str(self.q2), str(self.q3), str(self.q4)

                    target_member = None
                    if q4v and re.fullmatch(r"\d{17,19}", q4v):
                        try:
                            target_member = await modal_interaction.guild.fetch_member(int(q4v))
                        except Exception:
                            target_member = None

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

                    tickets_coll = colls["tickets"]
                    await tickets_coll.insert_one({
                        "_id": str(ticket.id),
                        "channelId": str(ticket.id),
                        "user1": str(modal_interaction.user.id),
                        "user2": str(target_member.id) if target_member else None,
                        "createdAt": datetime.utcnow()
                    })

                    await send_trade_embed(ticket, modal_interaction.user, target_member, q2v, q3v, q1v)
                    # Track ticket creation count locally (not in Mongo)
                    increment_ticket_count(modal_interaction.user.id)
                    if target_member:
                        increment_ticket_count(target_member.id)

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
            title="Azan's Middleman Service",
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
                f"• Make sure to read <#1414769580949377055> before making a ticket."
            ),
            color=EMBED_COLOR
        )

        existing = None
        async for msg in target.history(limit=50):
            if msg.author.id == ctx.bot.user.id and msg.embeds:
                if msg.embeds[0].title == "Azan's Middleman Service":
                    existing = msg
                    break

        if existing:
            await existing.edit(embed=embed, view=TicketPanelView())
            await ctx.reply("🔁 Setup panel updated.", mention_author=False)
        else:
            await target.send(embed=embed, view=TicketPanelView())
            await ctx.reply("✅ Setup complete.", mention_author=False)

    @commands.command(name="close")
    async def close_ticket(self, ctx: commands.Context):
        ch = ctx.channel
        cat_id = getattr(ch.category, "id", None)
    
        if not isinstance(ch, discord.TextChannel) or cat_id != TICKET_CATEGORY_ID:
            return await ctx.reply("❌ You can only close ticket channels!", mention_author=False)
    
        allowed = (
            any(r.id == MIDDLEMAN_ROLE_ID for r in ctx.author.roles)
            or ctx.author.guild_permissions.administrator
        )
        if not allowed:
            return await ctx.reply("❌ You don't have permission to close this ticket.", mention_author=False)
    
        colls = await collections()
        tickets_coll = colls["tickets"]
        mm_coll = colls["middlemen"]
        quota_coll = colls["weeklyQuota"]
    
        ticket_data = await tickets_coll.find_one({"channelId": str(ch.id)})
        claimed_by = ticket_data.get("claimedBy") if ticket_data else None
    
        if claimed_by:
            try:
                mm_id_for_db = int(claimed_by)
            except Exception:
                mm_id_for_db = claimed_by
    
            from datetime import datetime
            current_week = datetime.utcnow().isocalendar()[1]
    
            # ------------------- Update Middleman Leaderboard -------------------
            await mm_coll.update_one(
                {"_id": mm_id_for_db},
                {"$inc": {"completed": 1}, "$set": {"week": current_week}},
                upsert=True
            )
    
            # ------------------- Update Weekly Quota -------------------
            quota_doc = await quota_coll.find_one({"_id": mm_id_for_db})
            if quota_doc and quota_doc.get("week") == current_week:
                await quota_coll.update_one(
                    {"_id": mm_id_for_db},
                    {"$inc": {"completed": 1}}
                )
            else:
                await quota_coll.update_one(
                    {"_id": mm_id_for_db},
                    {"$set": {"completed": 1, "week": current_week}},
                    upsert=True
                )
    
            # ------------------- Refresh Boards -------------------
            quota_cog = ctx.bot.get_cog("Quota")
            if quota_cog:
                await quota_cog.send_quota_on_startup()  # safe: only sends if none exists
    
            mm_lb_cog = ctx.bot.get_cog("MiddlemanLeaderboard")
            if mm_lb_cog:
                for guild in ctx.bot.guilds:
                    await mm_lb_cog.update_or_create_lb(guild)
    
        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description="Select an option below to generate the transcript, log points, or delete the ticket.",
            color=0x2B2D31
        )
        embed.add_field(name="Ticket Name", value=ch.name, inline=True)
        embed.add_field(name="Closed By", value=ctx.author.mention, inline=True)
        embed.set_footer(text="Ticket Panel")
    
        await ctx.send(embed=embed, view=ClosePanel())
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Auto-clean Mongo when a ticket channel is deleted."""
        try:
            colls = await collections()
            tickets_coll = colls["tickets"]
            result = await tickets_coll.delete_one({"_id": str(channel.id)})
            if result.deleted_count > 0:
                print(f"🧹 [AUTO CLEANUP] Removed ticket entry for deleted channel {channel.id}")
        except Exception as e:
            print(f"[AUTO CLEANUP ERROR] {e}")
# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(Tickets(bot))