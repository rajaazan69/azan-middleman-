from discord.ext import commands
import discord

class Sticky(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sticky_map: dict[int, dict] = {}  # channel_id -> {message:str, message_id:int}

    @commands.command(name="setsticky")
    @commands.has_permissions(manage_messages=True)
    async def setsticky(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str):
        sent = await channel.send(message)
        self.sticky_map[channel.id] = {"message": message, "message_id": sent.id}
        await ctx.reply(f"✅ Sticky message set in {channel.mention}", mention_author=False)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not isinstance(message.channel, discord.TextChannel):
            return
        data = self.sticky_map.get(message.channel.id)
        if not data:
            return
        try:
            old = await message.channel.fetch_message(data["message_id"])
            await old.delete()
        except Exception:
            pass
        new_msg = await message.channel.send(data["message"])
        self.sticky_map[message.channel.id]["message_id"] = new_msg.id

async def setup(bot):
    await bot.add_cog(Sticky(bot))