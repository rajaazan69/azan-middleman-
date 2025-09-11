# utils/ticket_utils.py
import discord

async def parse_users_from_ticket_embed(channel: discord.TextChannel, bot):
    """
    Try to extract ticketOwnerId and otherTraderId from the very first embed in the channel.
    This assumes your ticket creation embed stored them in its fields.
    """
    try:
        async for msg in channel.history(limit=10, oldest_first=True):
            if msg.embeds:
                embed = msg.embeds[0]
                # Example: assuming embed description looks like "<@123> vs <@456>"
                if embed.description:
                    mentions = [u.id for u in msg.mentions]
                    if len(mentions) >= 2:
                        return mentions[0], mentions[1]
        return None, None
    except Exception as e:
        print(f"[ticket_utils] Failed to parse users: {e}")
        return None, None