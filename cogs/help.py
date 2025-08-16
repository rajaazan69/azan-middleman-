from discord.ext import commands
import discord

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Bot Commands",
            description="Here are all available commands for this bot:",
            color=0x00FF00
        )

        # List your current commands
        for command in self.bot.commands:
            # Skip hidden commands
            if command.hidden:
                continue
            embed.add_field(
                name=f"${command.name}",
                value=command.help or "No description provided",
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))