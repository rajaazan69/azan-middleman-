import re
import discord
from datetime import datetime
from discord.ext import commands
from utils.constants import EMBED_COLOR, TICKET_CATEGORY_ID, MIDDLEMAN_ROLE_ID, OWNER_ID
from utils.db import collections
from utils.constants import EMBED_COLOR, TICKET_CATEGORY_ID, MIDDLEMAN_ROLE_ID, OWNER_ID, LB_CHANNEL_ID, LB_MESSAGE_ID

# -------------------------
# Delete button view
# -------------------------
class TradeView(discord.ui.View):
    def __init__(self, owner_id: int, middleman_role_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.middleman_role_id = middleman_role_id

    @discord.ui.button(label="Delete Ticket", style=discord.ButtonStyle.danger, custom_id="delete_ticket")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (interaction.user.id == self.owner_id) or (self.middleman_role_id in [r.id for r in interaction.user.roles]):
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ You don’t have permission to delete this ticket.", ephemeral=True)

# -------------------------
# Ticket request panel view
# -------------------------
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Request Middleman", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        class TicketModal(discord.ui.Modal, title="Middleman Request"):
            q1 = discord.ui.TextInput(label="What's the trade?", required=True, max_length=200)
            q2 = discord.ui.TextInput(label="What's your side?", style=discord.TextStyle.long, required=True, max_length=500)
            q3 = discord.ui.TextInput(label="What's their side?", style=discord.TextStyle.long, required=True, max_length=500)
            q4 = discord.ui.TextInput(label="Their Discord ID?", required=True, max_length=20)

            async def on_submit(self, modal_interaction: discord.Interaction):
                await modal_interaction.response.defer(ephemeral=True, thinking=False)
                try:
                    colls = await collections()

                    # Check for existing ticket
                    cat = modal_interaction.guild.get_channel(TICKET_CATEGORY_ID)
                    if cat:
                        for ch in cat.channels:
                            ow = ch.overwrites_for(modal_interaction.user)
                            if ow.view_channel:
                                await modal_interaction.followup.send(
                                    f"❌ You already have an open ticket: {ch.mention}", ephemeral=True
                                )
                                return

                    q1v, q2v, q3v, q4v = str(self.q1), str(self.q2), str(self.q3), str(self.q4)
                    target_member = None
                    if re.fullmatch(r"\d{17,19}", q4v):
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

                    # Fetch ticket counts
                    count1 = await colls["tickets"].count_documents({"user1": str(modal_interaction.user.id)})
                    count2 = await colls["tickets"].count_documents({"user1": str(target_member.id)}) if target_member else 0

                    # New trade embed
                    trade_embed = discord.Embed(
                        title="• TRADE •",
                        description="Please wait for our **Middleman Team** to assist you.\n"
                                    "Make sure to abide by all rules and **vouch when the trade is over**.",
                        color=0x000000
                    )

                    user2_val = f"<@{target_member.id}>" if target_member else "`Unknown User`"

                    trade_embed.add_field(
                        name=f"{modal_interaction.user.mention} [{count1}]",
                        value=f"**Side:** {q2v}\n[​]({modal_interaction.user.display_avatar.url})",
                        inline=True
                    )

                    trade_embed.add_field(
                        name=f"{user2_val} [{count2}]",
                        value=f"**Side:** {q3v}\n[​]({target_member.display_avatar.url if target_member else ''})",
                        inline=True
                    )

                    trade_embed.add_field(
                        name="\u200b",
                        value=f"────────────────────\n<@{OWNER_ID}> <@&{MIDDLEMAN_ROLE_ID}>",
                        inline=False
                    )

                    view = TradeView(OWNER_ID, MIDDLEMAN_ROLE_ID)

                    await ticket.send(
                        content=f"<@{modal_interaction.user.id}> made a ticket with {user2_val}.",
                        embed=trade_embed,
                        view=view
                    )

                    await modal_interaction.followup.send(f"✅ Ticket created: {ticket.mention}", ephemeral=True)

                except Exception as e:
                    await modal_interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

        await interaction.response.send_modal(TicketModal())
# -------------------------
# Close ticket view
# -------------------------
import discord
from datetime import datetime
from utils.db import collections
from utils.constants import TICKET_CATEGORY_ID, LB_CHANNEL_ID, LB_MESSAGE_ID

class ClosePanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="TRANSCRIPT", style=discord.ButtonStyle.secondary, custom_id="ticket_transcript")
    async def transcript_btn(self, interaction: discord.Interaction, _):
        try:
            # Defer without editing original view
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=True)

            cog = interaction.client.get_cog("Transcripts")
            if not cog:
                return await interaction.followup.send(
                    "❌ Transcript system not loaded.", ephemeral=True
                )

            # ✅ Option A: just call generate_transcript, it handles sending
            await cog.generate_transcript(interaction, interaction.channel)

        except Exception as e:
            print("Transcript Button Error:", e)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Error generating transcript: {e}", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Error generating transcript: {e}", ephemeral=True
                )

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
                return await interaction.followup.send(
                    "❌ This button can only be used inside ticket channels.", ephemeral=True
                )

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

            # Leaderboard handling
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
                print(f"ℹ️ New leaderboard message created with ID: {lb_message.id}")
                await interaction.followup.send(
                    f"ℹ️ Created a new leaderboard message! ID: {lb_message.id}", ephemeral=True
                )

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

            await interaction.followup.send(
                f"✅ Logged 1 point for <@{'>, <@'.join(user_ids)}>.", ephemeral=True
            )

        except Exception as e:
            print("Log Points Button Error:", e)
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Something went wrong: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Something went wrong: {e}", ephemeral=True)
# -------------------------
# Main Cog
# -------------------------
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