import discord
from discord.ext import commands
from utils.constants import EMBED_COLOR, TICKET_CATEGORY_ID

GAME_DATA = {
    "gag": {
        "name": "GAG",
        "publicLink": "https://www.roblox.com/games/126884695634066/Grow-a-Garden?sortFilter=3",
        "privateLink": "https://www.roblox.com/share?code=2daaf72e32f63840b588d65a5cff53a7&type=Server",
        "thumbnail": "https://cdn.discordapp.com/attachments/1373070247795495116/1396644967665111142/IMG_6743.jpg"
    },
    "mm2": {
        "name": "MM2",
        "publicLink": "https://www.roblox.com/games/66654135/Murder-Mystery-2?sortFilter=3",
        "privateLink": "https://www.roblox.com/share?code=c1ac8abd3c27354e9db3979aad38b842&type=Server",
        "thumbnail": "https://cdn.discordapp.com/attachments/1373070247795495116/1396644976829661194/IMG_6744.jpg"
    },
    "sab": {
        "name": "SAB (Steal a Brainrot)",
        "publicLink": "https://www.roblox.com/games/109983668079237/Steal-a-Brainrot?sortFilter=3",
        "privateLink": "https://www.roblox.com/share?code=d99e8e73482e8342a3aa30fb59973322&type=Server",
        "thumbnail": "https://cdn.discordapp.com/attachments/1373070247795495116/1396644973134348288/IMG_6745.jpg"
    },
}

class Servers(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="servers")
    async def servers(self, ctx: commands.Context, game: str):
        game = game.lower()
        if game not in GAME_DATA:
            return await ctx.reply("❌ Choose one: gag | mm2 | sab", mention_author=False)

        if not isinstance(ctx.channel, discord.TextChannel) or ctx.channel.category_id != TICKET_CATEGORY_ID:
            return await ctx.reply("❌ This command can only be used inside ticket channels.", mention_author=False)

        g = GAME_DATA[game]
        embed = discord.Embed(
            title=f"Server Options for {g['name']}",
            description="**Please Choose Which Server You Would Be The Most Comfortable For The Trade In. Confirm The Middleman Which Server To Join**",
            color=EMBED_COLOR
        ).set_image(url=g["thumbnail"])

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Join Public Server", custom_id=f"public_{game}", style=discord.ButtonStyle.primary))
        view.add_item(discord.ui.Button(label="Join Private Server", custom_id=f"private_{game}", style=discord.ButtonStyle.secondary))
        await ctx.reply(embed=embed, view=view, mention_author=False)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type == discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id", "")
        if "_" not in cid: return
        kind, game = cid.split("_", 1)
        if game not in GAME_DATA: return
        g = GAME_DATA[game]
        is_public = (kind == "public")

        embed = discord.Embed(
            title="Server Chosen",
            description=f"**{interaction.user.mention} has chosen to trade in the {'Public' if is_public else 'Private'} Server.**",
            color=EMBED_COLOR
        )
        link = g["publicLink"] if is_public else g["privateLink"]
        embed.add_field(name="🔗 Click to Join:", value=f"[{'Public' if is_public else 'Private'} Server Link]({link})", inline=False)
        embed.set_image(url=g["thumbnail"])

        if not interaction.response.is_done():
            await interaction.response.defer()
        await interaction.edit_original_response(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(Servers(bot))