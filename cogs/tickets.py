import re
import os
import discord
from discord.ext import commands
from discord import app_commands
from utils.constants import (
    EMBED_COLOR, TICKET_CATEGORY_ID, MIDDLEMAN_ROLE_ID, OWNER_ID
)
from utils.db import collections


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
                # ✅ Acknowledge immediately
                await modal_interaction.response.defer(ephemeral=True, thinking=False)

                try:
                    colls = await collections()

                    # Prevent multiple tickets with existing permission-overwrite check
                    cat = modal_interaction.guild.get_channel(TICKET_CATEGORY_ID)
                    if cat:
                        for ch in cat.channels:
                            ow = ch.overwrites_for(modal_interaction.user)
                            if ow.view_channel:
                                await modal_interaction.followup.send(
                                    f"❌ You already have an open ticket: {ch.mention}", ephemeral=True
                                )
                                return

                    q1v = str(self.q1)
                    q2v = str(self.q2)
                    q3v = str(self.q3)
                    q4v = str(self.q4)

                    valid = re.fullmatch(r"\d{17,19}", q4v or "")
                    target_member = None
                    if valid:
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

                    cat = modal_interaction.guild.get_channel(TICKET_CATEGORY_ID)
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

                    # info + details embed
                    info = discord.Embed(
                        description=f"Please wait for our **Middleman Team** to assist you.\nMake sure to abide by all the rules and **vouch when the trade is over**.",
                        color=EMBED_COLOR
                    )
                    user2_val = f"<@{target_member.id}>" if target_member else "`Unknown User`"
                    details = discord.Embed(title="Middleman Request", color=0xFFFFFF)
                    details.set_thumbnail(url=modal_interaction.user.display_avatar.url)
                    details.add_field(name="**User 1**", value=f"<@{modal_interaction.user.id}>", inline=True)
                    details.add_field(name="**User 2**", value=user2_val, inline=True)
                    details.add_field(name="\u200b", value="\u200b", inline=False)
                    details.add_field(name="**Trade Details**", value=f"> {q1v}", inline=False)
                    details.add_field(name="**User 1 is giving**", value=f"> {q2v}", inline=False)
                    details.add_field(name="**User 2 is giving**", value=f"> {q3v}", inline=False)

                    await ticket.send(
                        content=f"<@{modal_interaction.user.id}> made a ticket with {user2_val}.\nPlease wait until <@{OWNER_ID}> assists you.",
                        embeds=[info, details]
                    )

                    await modal_interaction.followup.send(f"✅ Ticket created: {ticket.mention}", ephemeral=True)

                except Exception as e:
                    await modal_interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

        await interaction.response.send_modal(TicketModal())


class ClosePanel(discord.ui.View):
    def __init__(self, owner_tag: str, ticket_owner_id: int | None):
        super().__init__(timeout=None)
        self.owner_tag = owner_tag
        self.ticket_owner_id = ticket_owner_id

    @discord.ui.button(label="TRANSCRIPT", style=discord.ButtonStyle.secondary, custom_id="ticket_transcript")
    async def transcript_btn(self, interaction: discord.Interaction, _):
        await interaction.response.defer(ephemeral=True)
        cog = interaction.client.get_cog("Transcripts")
        await cog.generate_transcript(interaction, interaction.channel)  # re-use transcript cog

    @discord.ui.button(label="DELETE", style=discord.ButtonStyle.danger, custom_id="ticket_delete")
    async def delete_btn(self, interaction: discord.Interaction, _):
        await interaction.response.defer()
        await interaction.channel.delete()

    @discord.ui.button(label="LOG POINTS", style=discord.ButtonStyle.success, custom_id="ticket_log_points")
    async def log_points_btn(self, interaction: discord.Interaction, _):
        await interaction.response.defer(ephemeral=True)
        cog = interaction.client.get_cog("Transcripts")
        await cog.log_points(interaction)


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

        # find ticket owner by perms
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
        await ctx.send(embed=embed, view=ClosePanel(str(ctx.author), ticket_owner_id))


async def setup(bot):
    await bot.add_cog(Tickets(bot))