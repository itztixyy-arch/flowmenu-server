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

    # CHECK & ADD UNIQUE PLAYER ID TO HISTORY
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
        :root {
            --bg-primary: #0a0b0e;
            --bg-secondary: #12141a;
            --bg-card: #1a1d26;
            --accent-color: #6366f1;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --border-color: #262936;
            --status-green: #10b981;
            --tag-red: #ef4444;
        }

        * {
            box-sizing: border-box;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            transition: all 0.2s ease-in-out;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-main);
            display: flex;
            margin: 0;
            height: 100vh;
            overflow: hidden;
        }

        /* Vertically Centered Main Left Dashboard Area */
        .main-content {
            flex: 1;
            padding: 40px;
            display: flex;
            flex-direction: column;
            justify-content: center; /* Vertically Centers along Y-axis */
            align-items: center;     /* Horizontally Centers Content Container */
            overflow-y: auto;
        }

        /* Container that locks width for a clean centered layout */
        .content-wrapper {
            width: 100%;
            max-width: 900px;
        }

        .header-section {
            margin-bottom: 28px;
        }

        .dashboard-title {
            font-size: 13px;
            font-weight: 700;
            color: var(--accent-color);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 10px;
            text-align: left;
        }

        /* HUGE ONLINE COUNT HEADER */
        .big-online-banner {
            background: linear-gradient(135deg, #171a24 0%, #11131b 100%);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 28px 36px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
        }

        .big-online-text {
            font-size: 44px;
            font-weight: 900;
            letter-spacing: -1px;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .big-online-text span {
            color: var(--status-green);
        }

        .live-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            background-color: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.25);
            padding: 8px 16px;
            border-radius: 20px;
            color: var(--status-green);
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        .pulse-dot {
            width: 10px;
            height: 10px;
            background-color: var(--status-green);
            border-radius: 50%;
            box-shadow: 0 0 12px var(--status-green);
            animation: pulse 1.8s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.9); opacity: 0.7; }
            50% { transform: scale(1.3); opacity: 1; }
            100% { transform: scale(0.9); opacity: 0.7; }
        }

        /* Active Sessions Grid */
        .section-title {
            font-size: 13px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
        }

        .player-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 16px;
            max-height: 400px;
            overflow-y: auto;
            padding-right: 4px;
        }

        .player-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }

        .player-card:hover {
            transform: translateY(-2px);
            border-color: var(--accent-color);
        }

        .player-card .nickname {
            font-weight: 800;
            font-size: 17px;
            color: #ffffff;
        }

        .player-card .info-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            color: var(--text-muted);
        }

        .player-card .room-tag {
            background-color: rgba(239, 68, 68, 0.15);
            color: var(--tag-red);
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 3px 10px;
            border-radius: 6px;
            font-family: monospace;
            font-weight: 700;
            font-size: 12px;
        }

        .player-card .id-tag {
            font-family: monospace;
            background-color: var(--bg-secondary);
            padding: 3px 8px;
            border-radius: 5px;
            color: #d1d5db;
        }

        .empty-state {
            background-color: var(--bg-secondary);
            border: 2px dashed var(--border-color);
            border-radius: 14px;
            padding: 50px 20px;
            text-align: center;
            color: var(--text-muted);
            grid-column: 1 / -1;
            font-size: 14px;
        }

        /* Right Sidebar (History) */
        .sidebar {
            width: 360px;
            background-color: var(--bg-secondary);
            border-left: 1px solid var(--border-color);
            padding: 36px 28px;
            display: flex;
            flex-direction: column;
        }

        .sidebar h2 {
            font-size: 18px;
            margin-top: 0;
            margin-bottom: 20px;
            color: #ffffff;
            font-weight: 800;
            letter-spacing: 0.5px;
        }

        .search-box {
            width: 100%;
            padding: 14px 18px;
            background-color: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            color: #ffffff;
            outline: none;
            margin-bottom: 20px;
            font-size: 14px;
        }

        .search-box:focus {
            border-color: var(--accent-color);
        }

        .stored-list {
            list-style: none;
            padding: 0;
            margin: 0;
            overflow-y: auto;
            flex: 1;
        }

        .stored-item {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            padding: 14px;
            margin-bottom: 10px;
            border-radius: 8px;
            font-size: 13px;
            font-family: monospace;
            word-break: break-all;
            color: #d1d5db;
        }
    </style>
</head>
<body>

    <!-- Main Content Vertically Centered -->
    <div class="main-content">
        <div class="content-wrapper">
            <div class="header-section">
                <div class="dashboard-title">FlowMenu Dashboard</div>
                
                <div class="big-online-banner">
                    <div class="big-online-text">
                        ONLINE: <span id="onlineCount">0</span>
                    </div>
                    <div class="live-indicator">
                        <div class="pulse-dot"></div>
                        LIVE API
                    </div>
                </div>
            </div>

            <div class="section-title">Connected Active Players</div>
            
            <div id="activePlayersGrid" class="player-grid">
                <div class="empty-state">No players currently connected</div>
            </div>
        </div>
    </div>

    <!-- Sidebar: History / Stored Player IDs -->
    <div class="sidebar">
        <h2>History</h2>
        <input type="text" id="searchInput" class="search-box" placeholder="Search Player ID..." onkeyup="filterStoredPlayers()">
        
        <ul id="storedList" class="stored-list">
            <!-- Populated via JavaScript -->
        </ul>
    </div>

    <script>
        let allStoredIds = [];

        async function fetchStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                // Update Big Online Counter
                document.getElementById('onlineCount').innerText = data.online_count || 0;

                // Render Connected Active Players
                renderActivePlayers(data.players || []);

                // Update & Render History List
                allStoredIds = data.stored_player_ids || [];
                renderStoredPlayers(allStoredIds);
            } catch (err) {
                console.error("Error updating stats:", err);
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
                        <span>Room Code</span>
                        <span class="room-tag">${escapeHtml(p.room)}</span>
                    </div>
                    <div class="info-row">
                        <span>Player ID</span>
                        <span class="id-tag">${escapeHtml(p.player_id)}</span>
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
                list.innerHTML = '<li class="stored-item" style="color:#6b7280; text-align:center;">No IDs found</li>';
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

        // Auto-refresh every 3 seconds
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
