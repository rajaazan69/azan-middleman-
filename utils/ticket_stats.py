import json, os

STATS_FILE = "db/ticket_stats.json"

def load_ticket_stats():
    if not os.path.exists(STATS_FILE):
        return {}
    with open(STATS_FILE, "r") as f:
        return json.load(f)

def save_ticket_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)

def increment_ticket_count(user_id: int):
    stats = load_ticket_stats()
    uid = str(user_id)
    if uid not in stats:
        stats[uid] = {"total": 0}
    stats[uid]["total"] += 1
    save_ticket_stats(stats)

def get_ticket_count(user_id: int) -> int:
    stats = load_ticket_stats()
    return stats.get(str(user_id), {}).get("total", 0)