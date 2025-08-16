import discord
from discord.ext import commands

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx, channel: discord.TextChannel):
        # Build embed
        embed = discord.Embed(
            color=0x000000,
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
                "• Make sure to read <#1373027499738398760> before making a ticket."
            )
        )

        # Button
        view = discord.ui.View()
        button = discord.ui.Button(
            label="Request Middleman",
            style=discord.ButtonStyle.primary,
            custom_id="openTicket"
        )
        view.add_item(button)

        # Send panel
        await channel.send(embed=embed, view=view)
        await ctx.send("✅ Setup complete.", delete_after=5)

async def setup(bot):
    await bot.add_cog(Setup(bot))