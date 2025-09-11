# cogs/format.py

import discord
from discord.ext import commands
from utils.constants import EMBED_COLOR, TICKET_CATEGORY_ID
from utils.db import collections


class FormatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="format", help="Provide trade details format inside a ticket.")
    async def format_cmd(self, ctx: commands.Context):
        ch = ctx.channel
        cat_id = getattr(ch.category, "id", None)

        # ✅ Only works inside ticket category
        if not isinstance(ch, discord.TextChannel) or cat_id != TICKET_CATEGORY_ID:
            return await ctx.reply("❌ You can only use this in a ticket channel.", mention_author=False)

        # ✅ Staff only
        if not (ctx.author.guild_permissions.manage_messages or ctx.author.guild_permissions.administrator):
            return await ctx.reply("❌ Only staff can use this command.", mention_author=False)

        await ctx.reply("⏳ Preparing trade format...", mention_author=False)

        try:
            colls = await collections()
            tickets_coll = colls["tickets"]
            ticket_data = await tickets_coll.find_one({"channelId": str(ch.id)})

            user1 = ticket_data.get("user1") if ticket_data else None
            user2 = ticket_data.get("user2") if ticket_data else None

            if not (user1 and user2):
                return await ctx.send("❌ Could not find both traders in the database. Please ping them manually.")

            # ✅ Trade format text
            trade_format = (
                "1. What is your roblox username/ingame username?\n"
                "2. What is your side of the trade?\n"
                "3. Can you join private servers? (13+)\n"
                "4. Do you agree to vouch after the trade is done?"
            )

            embed = discord.Embed(
                title="📒 Fill Out Trade Details",
                description=(
                    "To proceed, please **answer the questions below** and fill in all the details for the trade.\n\n"
                    "👉 You may ping the middleman when both traders are done filling in the details."
                ),
                color=EMBED_COLOR
            )
            embed.add_field(name="Questions", value=f"```{trade_format}```", inline=False)
            embed.set_footer(text="Fill this out accurately. The middleman will confirm before proceeding.")

            await ctx.send(
                content=f"<@{user1}> and <@{user2}>, please fill out the trade details below:",
                embed=embed
            )

        except Exception as e:
            await ctx.send(f"❌ Error while sending format: {e}")


async def setup(bot):
    await bot.add_cog(FormatCog(bot))