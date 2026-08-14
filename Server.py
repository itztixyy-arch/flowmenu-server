import os
import time
import re
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Active player session storage (live status)
active_clients = {}
TIMEOUT = 12

# Unique stored player IDs (so duplicates are ignored)
stored_player_ids = set()

def cleanup_inactive_players():
    current_time = time.time()
    # Remove timed-out players
    expired = [name for name, data in active_clients.items() if current_time - data["last_seen"] > TIMEOUT]
    for name in expired:
        del active_clients[name]

    # Clean up ghost / uninitialized names
    ghost_keys = [k for k in active_clients.keys() if k.lower() == "unknown" or re.match(r"^gorilla\d+$", k.lower())]
    for ghost in ghost_keys:
        del active_clients[ghost]

# ----------------- API ROUTES -----------------

@app.route('/ping', methods=['POST'])
def ping():
    cleanup_inactive_players()
    data = request.get_json(silent=True) or {}
    
    player_name = data.get("player_name", "").strip()
    player_id = data.get("player_id", "").strip()
    room_code = data.get("room_code", "NOT IN ROOM")

    if not player_name or player_name.lower() == "unknown" or re.match(r"^gorilla\d+$", player_name.lower()):
        return jsonify({"status": "ignored", "reason": "unloaded_nickname"}), 200

    # Save active session details
    active_clients[player_name] = {
        "room": room_code,
        "player_id": player_id,
        "last_seen": time.time()
    }

    # CHECK & ADD UNIQUE PLAYER ID
    if player_id:
        stored_player_ids.add(player_id)  # Sets automatically ignore duplicates

    return jsonify({"status": "ok", "online_count": len(active_clients)}), 200

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
        "stored_player_ids": list(stored_player_ids) # Sends unique player list to website
    })

# ----------------- WEB FRONTEND ROUTE -----------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>FlowMenu Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #1e1f22;
            color: #ffffff;
            display: flex;
            margin: 0;
            height: 100vh;
            overflow: hidden;
        }

        /* Main Dashboard Content Area */
        .main-content {
            flex: 1;
            padding: 30px;
            overflow-y: auto;
        }

        .card {
            background-color: #2b2d31;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        /* Right Side Panel Styling */
        .sidebar {
            width: 320px;
            background-color: #2b2d31;
            border-left: 2px solid #3f4147;
            padding: 20px;
            display: flex;
            flex-direction: column;
        }

        .sidebar h2 {
            font-size: 18px;
            margin-top: 0;
            margin-bottom: 15px;
            color: #5865f2;
        }

        /* Search Bar Input */
        .search-box {
            width: 100%;
            padding: 10px;
            box-sizing: border-box;
            background-color: #1e1f22;
            border: 1px solid #4e5058;
            border-radius: 5px;
            color: white;
            outline: none;
            margin-bottom: 15px;
            font-size: 14px;
        }

        .search-box:focus {
            border-color: #5865f2;
        }

        /* Stored Players List Container */
        .player-list {
            list-style: none;
            padding: 0;
            margin: 0;
            overflow-y: auto;
            flex: 1;
        }

        .player-item {
            background-color: #313338;
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 6px;
            font-size: 13px;
            font-family: monospace;
            word-break: break-all;
            border-left: 3px solid #5865f2;
        }
    </style>
</head>
<body>

    <!-- Main Content Body -->
    <div class="main-content">
        <h1>FlowMenu Live Dashboard</h1>
        <div class="card">
            <h3>Active Online Players: <span id="onlineCount">0</span></h3>
        </div>
    </div>

    <!-- Right Side Panel -->
    <div class="sidebar">
        <h2>Stored Player IDs</h2>
        
        <!-- Search Bar -->
        <input type="text" id="searchInput" class="search-box" placeholder="Search Player ID..." onkeyup="filterPlayers()">
        
        <!-- Player ID List -->
        <ul id="playerList" class="player-list">
            <!-- Populated automatically -->
        </ul>
    </div>

    <script>
        let allStoredIds = [];

        async function fetchStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('onlineCount').innerText = data.online_count || 0;

                allStoredIds = data.stored_player_ids || [];
                renderPlayerList(allStoredIds);
            } catch (err) {
                console.error("Error fetching web stats:", err);
            }
        }

        function renderPlayerList(idArray) {
            const listElement = document.getElementById('playerList');
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            
            listElement.innerHTML = '';

            // Filter through stored IDs
            const filtered = idArray.filter(id => id.toLowerCase().includes(searchTerm));

            if (filtered.length === 0) {
                listElement.innerHTML = '<li class="player-item" style="border-left:none; color:#888;">No IDs found</li>';
                return;
            }

            filtered.forEach(id => {
                const li = document.createElement('li');
                li.className = 'player-item';
                li.textContent = id;
                listElement.appendChild(li);
            });
        }

        function filterPlayers() {
            renderPlayerList(allStoredIds);
        }

        // Refresh stats every 3 seconds
        setInterval(fetchStats, 3000);
        fetchStats();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
