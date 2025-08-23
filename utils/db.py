import os
from motor.motor_asyncio import AsyncIOMotorClient

_mongo: AsyncIOMotorClient | None = None
_db = None

async def get_db():
    """
    Returns the database instance.
    Initializes connection if it hasn't been made yet.
    """
    global _mongo, _db
    if _db is not None:
        return _db

    uri = os.getenv("MONGO_URI")
    if not uri or not uri.startswith(("mongodb://", "mongodb+srv://")):
        raise ValueError(
            "MONGO_URI is missing or invalid. Must start with 'mongodb://' or 'mongodb+srv://'"
        )

    _mongo = AsyncIOMotorClient(uri)
    _db = _mongo["ticketbot"]  # Database name
    return _db

async def collections():
    """
    Returns a dict of all collections used by the bot.
    Example usage:
        colls = await collections()
        await colls['tickets'].find_one({...})
    """
    db = await get_db()
    return {
        "tags": db["tags"],
        "tickets": db["tickets"],
        "transcripts": db["transcripts"],
        "clientPoints": db["clientPoints"],
        "middlemen": db["middlemen"],  # Added so close_ticket works
    }