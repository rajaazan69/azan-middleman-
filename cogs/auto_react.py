import discord
from discord.ext import commands


TARGET_CHANNEL_ID = 1373027974827212923  
EMOJI = "<:emoji_46:1428129673237237781>"

class AutoReact(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        
        if message.author.bot:
            return

        
        if message.channel.id == TARGET_CHANNEL_ID:
            try:

                emoji = discord.utils.get(message.guild.emojis, name="emoji_46")
                if emoji:
                    await message.add_reaction(emoji)
                else:

                    await message.add_reaction("<:emoji_46:1428129673237237781>")
            except Exception as e:
                print(f"[AutoReact Error] {e}")

# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(AutoReact(bot))