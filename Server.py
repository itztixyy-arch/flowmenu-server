import os
import time
import re
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Active live players (room/session tracking)
active_clients = {}
TIMEOUT = 12

# Unique stored players list (stores unique Player IDs)
stored_player_ids = set()

def cleanup_inactive_players():
    current_time = time.time()
    expired = [name for name, data in active_clients.items() if current_time - data["last_seen"] > TIMEOUT]
    for name in expired:
        del active_clients[name]

    ghost_keys = [k for k in active_clients.keys() if k.lower() == "unknown" or re.match(r"^gorilla\d+$", k.lower())]
    for ghost in ghost_keys:
        del active_clients[ghost]

@app.route('/ping', methods=['POST'])
def ping():
    cleanup_inactive_players()
    data = request.get_json(silent=True) or {}
    
    player_name = data.get("player_name", "").strip()
    player_id = data.get("player_id", "").strip()
    room_code = data.get("room_code", "NOT IN ROOM")

    if not player_name or player_name.lower() == "unknown" or re.match(r"^gorilla\d+$", player_name.lower()):
        return jsonify({"status": "ignored", "reason": "unloaded_nickname"}), 200

    # Store active session info
    active_clients[player_name] = {
        "room": room_code,
        "player_id": player_id,
        "last_seen": time.time()
    }

    # CHECK & ADD UNIQUE PLAYER ID
    already_stored = False
    if player_id:
        if player_id in stored_player_ids:
            already_stored = True
        else:
            stored_player_ids.add(player_id)  # Added because it's new

    return jsonify({
        "status": "ok", 
        "online_count": len(active_clients),
        "player_id_added": not already_stored
    }), 200

@app.route('/api/stats', methods=['GET'])
def get_stats():
    cleanup_inactive_players()
    players = [
        {"nickname": name, "room": data["room"], "player_id": data.get("player_id", "N/A")}
        for name, data in active_clients.items()
    ]
    return jsonify({
        "online_count": len(active_clients),
        "players": players,
        "stored_player_ids": list(stored_player_ids)  # Returns all unique stored IDs
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
