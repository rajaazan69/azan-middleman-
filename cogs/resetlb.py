@commands.command(name="resetlb", help="Resets the client points leaderboard (admin/owner only).")
async def resetlb(self, ctx: commands.Context):
    OWNER_ID = 1356149794040446998  # Replace with your Discord ID

    # Check permissions
    is_owner = ctx.author.id == OWNER_ID
    is_admin = ctx.author.guild_permissions.administrator

    if not is_owner and not is_admin:
        return await ctx.send("❌ You do not have permission to reset the leaderboard.", delete_after=10)

    try:
        # Clear all points from MongoDB collection
        colls = await collections()
        await colls["clientPoints"].delete_many({})

        # Update leaderboard message
        leaderboard_channel_id = int(os.getenv("LEADERBOARD_CHANNEL_ID"))
        leaderboard_message_id = int(os.getenv("LEADERBOARD_MESSAGE_ID"))
        channel = ctx.guild.get_channel(leaderboard_channel_id)
        if channel:
            message = await channel.fetch_message(leaderboard_message_id)
            embed = discord.Embed(
                title="🏆 Client Leaderboard",
                description="No points recorded yet!",
                color=0xFFD700,
                timestamp=datetime.utcnow()
            )
            await message.edit(embed=embed)

        await ctx.send("✅ Leaderboard has been reset.", delete_after=10)

    except Exception as e:
        print("❌ Error resetting leaderboard:", e)
        await ctx.send("❌ Failed to reset leaderboard.", delete_after=10)
