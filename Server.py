import os
import time
import re
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Active player session storage (live status)
active_clients = {}
TIMEOUT = 12

# Unique stored player IDs (duplicates ignored)
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
        "player_id": player_id if player_id else "Unknown ID",
        "last_seen": time.time()
    }

    # CHECK & ADD UNIQUE PLAYER ID
    if player_id:
        stored_player_ids.add(player_id)

    return jsonify({"status": "ok", "online_count": len(active_clients)}), 200

@app.route('/api/stats', methods=['GET'])
def get_stats():
    cleanup_inactive_players()
    players = [
        {
            "nickname": name, 
            "room": data["room"], 
            "player_id": data.get("player_id", "N/A")
        }
        for name, data in active_clients.items()
    ]
    return jsonify({
        "online_count": len(active_clients),
        "players": players,
        "stored_player_ids": list(stored_player_ids)
    })

# ----------------- WEB FRONTEND ROUTE -----------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FlowMenu Live Dashboard</title>
    <style>
        * {
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        body {
            background-color: #111214;
            color: #dbdee1;
            display: flex;
            margin: 0;
            height: 100vh;
            overflow: hidden;
        }

        /* Main Left Dashboard Area */
        .main-content {
            flex: 1;
            padding: 30px;
            overflow-y: auto;
        }

        .header-card {
            background-color: #1e1f22;
            border: 1px solid #2b2d31;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .header-card h1 {
            margin: 0;
            font-size: 22px;
            color: #fff;
        }

        .badge {
            background-color: #2b2d31;
            border: 1px solid #35363c;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
        }

        .badge span {
            color: #23a55a;
        }

        /* Live Active Players Table */
        .section-title {
            font-size: 16px;
            font-weight: 600;
            color: #949ba4;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .player-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }

        .player-card {
            background-color: #1e1f22;
            border: 1px solid #2b2d31;
            border-radius: 10px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            border-left: 4px solid #5865f2;
        }

        .player-card .nickname {
            font-weight: 700;
            font-size: 16px;
            color: #fff;
        }

        .player-card .info-row {
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            color: #949ba4;
        }

        .player-card .room-tag {
            background-color: #2b2d31;
            color: #f23f43;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: monospace;
            font-weight: 600;
        }

        .empty-state {
            background-color: #1e1f22;
            border: 1px dashed #2b2d31;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            color: #80848e;
            grid-column: 1 / -1;
        }

        /* Right Side Panel Styling */
        .sidebar {
            width: 320px;
            background-color: #1e1f22;
            border-left: 1px solid #2b2d31;
            padding: 24px;
            display: flex;
            flex-direction: column;
        }

        .sidebar h2 {
            font-size: 16px;
            margin-top: 0;
            margin-bottom: 16px;
            color: #fff;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .search-box {
            width: 100%;
            padding: 12px;
            background-color: #111214;
            border: 1px solid #2b2d31;
            border-radius: 8px;
            color: #fff;
            outline: none;
            margin-bottom: 16px;
            font-size: 14px;
        }

        .search-box:focus {
            border-color: #5865f2;
        }

        .stored-list {
            list-style: none;
            padding: 0;
            margin: 0;
            overflow-y: auto;
            flex: 1;
        }

        .stored-item {
            background-color: #2b2d31;
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 6px;
            font-size: 13px;
            font-family: monospace;
            word-break: break-all;
            color: #b5bac1;
        }
    </style>
</head>
<body>

    <!-- Main Content: Active Players -->
    <div class="main-content">
        <div class="header-card">
            <h1>FlowMenu Dashboard</h1>
            <div class="badge">Active Players: <span id="onlineCount">0</span></div>
        </div>

        <div class="section-title">Live Active Sessions</div>
        <div id="activePlayersGrid" class="player-grid">
            <div class="empty-state">No players currently connected</div>
        </div>
    </div>

    <!-- Sidebar: Unique Player IDs -->
    <div class="sidebar">
        <h2>History</h2>
        <input type="text" id="searchInput" class="search-box" placeholder="Search Player ID..." onkeyup="filterStoredPlayers()">
        
        <ul id="storedList" class="stored-list">
            <!-- Dynamically populated -->
        </ul>
    </div>

    <script>
        let allStoredIds = [];

        async function fetchStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                // Update player counter
                document.getElementById('onlineCount').innerText = data.online_count || 0;

                // Render Live Active Players
                renderActivePlayers(data.players || []);

                // Save & Render Stored Player IDs
                allStoredIds = data.stored_player_ids || [];
                renderStoredPlayers(allStoredIds);
            } catch (err) {
                console.error("Error fetching stats:", err);
            }
        }

        function renderActivePlayers(players) {
            const grid = document.getElementById('activePlayersGrid');
            grid.innerHTML = '';

            if (players.length === 0) {
                grid.innerHTML = '<div class="empty-state">No players currently connected</div>';
                return;
            }

            players.forEach(p => {
                const card = document.createElement('div');
                card.className = 'player-card';
                card.innerHTML = `
                    <div class="nickname">${escapeHtml(p.nickname)}</div>
                    <div class="info-row">
                        <span>Room Code:</span>
                        <span class="room-tag">${escapeHtml(p.room)}</span>
                    </div>
                    <div class="info-row">
                        <span>ID:</span>
                        <span style="font-family: monospace;">${escapeHtml(p.player_id)}</span>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        function renderStoredPlayers(idArray) {
            const list = document.getElementById('storedList');
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            list.innerHTML = '';

            const filtered = idArray.filter(id => id.toLowerCase().includes(searchTerm));

            if (filtered.length === 0) {
                list.innerHTML = '<li class="stored-item" style="color:#80848e;">No IDs matched</li>';
                return;
            }

            filtered.forEach(id => {
                const li = document.createElement('li');
                li.className = 'stored-item';
                li.textContent = id;
                list.appendChild(li);
            });
        }

        function filterStoredPlayers() {
            renderStoredPlayers(allStoredIds);
        }

        function escapeHtml(str) {
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        // Auto-refresh stats every 3 seconds
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
