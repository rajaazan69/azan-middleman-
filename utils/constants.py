import os

OWNER_ID = int(os.getenv("OWNER_ID", "0"))
MIDDLEMAN_ROLE_ID = int(os.getenv("MIDDLEMAN_ROLE_ID", "0"))
PANEL_CHANNEL_ID = int(os.getenv("PANEL_CHANNEL_ID", "0"))
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "0"))
TRANSCRIPT_CHANNEL_ID = int(os.getenv("TRANSCRIPT_CHANNEL_ID", "0"))
LB_CHANNEL_ID = int(os.getenv("LB_CHANNEL_ID", "0"))
LB_MESSAGE_ID = int(os.getenv("LB_MESSAGE_ID", "0"))

BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")
PORT = int(os.getenv("PORT", "25267"))

# Design
EMBED_COLOR = 0x000000