import os
from motor.motor_asyncio import AsyncIOMotorClient

_mongo = None
_db = None

async def get_db():
    global _mongo, _db
    if _db is not None:  # <-- explicit check
        return _db

    uri = os.getenv("MONGO_URI")
    if not uri or not uri.startswith(("mongodb://", "mongodb+srv://")):
        raise ValueError("MONGO_URI is missing or invalid. Must start with 'mongodb://' or 'mongodb+srv://'")

    _mongo = AsyncIOMotorClient(uri)
    _db = _mongo["ticketbot"]
    return _db

async def collections():
    db = await get_db()
    return {
        "tags": db["tags"],
        "tickets": db["tickets"],
        "transcripts": db["transcripts"],
        "clientPoints": db["clientPoints"],
    }