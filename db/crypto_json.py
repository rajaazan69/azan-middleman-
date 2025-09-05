import json
import os

DB_PATH = "crypto.json"

# --- Load JSON ---
def load_data():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, "r") as f:
        return json.load(f)

# --- Save JSON ---
def save_data(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=4)

# --- Save a crypto address ---
def save_crypto_address(user_id: str, crypto_type: str, address: str):
    data = load_data()
    if user_id not in data:
        data[user_id] = {}
    data[user_id][crypto_type] = address
    save_data(data)

# --- Get one address ---
def get_crypto_address(user_id: str, crypto_type: str):
    data = load_data()
    return data.get(user_id, {}).get(crypto_type)

# --- Get all addresses for a user ---
def get_all_crypto_addresses(user_id: str):
    data = load_data()
    return data.get(user_id, {})