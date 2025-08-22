import discord
from discord.ext import commands

WELCOME_CHANNEL_ID = 1373078546422960148  # Replace with your welcome channel ID
VOUCHES_CHANNEL_ID = 1373027974827212923
PROOFS_CHANNEL_ID = 1373027988391596202

class WelcomeMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        print(f"{member} joined {member.guild.name}")

        welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if not welcome_channel:
            return

        embed = discord.Embed(
            color=0x000000,
            description=(
                f"Welcome to **Azan’s Middleman Services** {member}!\n\n"
                f"To view vouches: <#{VOUCHES_CHANNEL_ID}>\n"
                f"To view proofs: <#{PROOFS_CHANNEL_ID}>\n\n"
                "We hope you enjoy your stay here!"
            ),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")

        await welcome_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(WelcomeMessage(bot))