import os
import time
import re
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Active player session storage
active_clients = {}
TIMEOUT = 12

# Unique stored player IDs
stored_player_ids = set()

def cleanup_inactive_players():
    current_time = time.time()
    expired = [name for name, data in active_clients.items() if current_time - data["last_seen"] > TIMEOUT]
    for name in expired:
        del active_clients[name]

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

    active_clients[player_name] = {
        "room": room_code,
        "player_id": player_id if player_id else "Unknown ID",
        "last_seen": time.time()
    }

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

# ----------------- FRONTEND UI -----------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FlowMenu Live Dashboard</title>
    <style>
        :root {
            --accent: #6366f1;
            --bg-glass: rgba(18, 20, 29, 0.70);
            --border-glass: rgba(255, 255, 255, 0.1);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --green: #10b981;
            --red: #ef4444;
        }

        * {
            box-sizing: border-box;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: #060709;
            color: var(--text-main);
            height: 100vh;
            overflow: hidden;
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        /* BIG WHITE BUBBLE IN THE MIDDLE */
        .white-center-orb {
            position: absolute;
            width: 650px;
            height: 650px;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0.03) 50%, rgba(0,0,0,0) 70%);
            border-radius: 50%;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            filter: blur(60px);
            z-index: 0;
            pointer-events: none;
            animation: pulseWhite 8s ease-in-out infinite alternate;
        }

        @keyframes pulseWhite {
            0% { transform: translate(-50%, -50%) scale(0.95); opacity: 0.8; }
            100% { transform: translate(-50%, -50%) scale(1.1); opacity: 1; }
        }

        /* ANIMATED GRID PATTERN BACKGROUND */
        .bg-grid-animation {
            position: absolute;
            top: 0;
            left: 0;
            width: 200%;
            height: 200%;
            background-image: radial-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px);
            background-size: 32px 32px;
            z-index: 0;
            opacity: 0.4;
            animation: moveGrid 20s linear infinite;
        }

        @keyframes moveGrid {
            0% { transform: translate(0, 0); }
            100% { transform: translate(-32px, -32px); }
        }

        /* Main Dashboard Container */
        .dashboard-container {
            position: relative;
            z-index: 10;
            display: flex;
            gap: 28px;
            width: 90%;
            max-width: 1250px;
            height: 80vh;
            align-items: center;
        }

        /* Left Main Panel */
        .main-card {
            flex: 1.4;
            background: var(--bg-glass);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid var(--border-glass);
            border-radius: 24px;
            padding: 36px;
            height: 100%;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
        }

        .header-title {
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 2px;
            color: var(--accent);
            text-transform: uppercase;
            margin-bottom: 12px;
        }

        .online-banner {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-glass);
            border-radius: 18px;
            padding: 24px 30px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
        }

        .online-count {
            font-size: 42px;
            font-weight: 900;
            letter-spacing: -1px;
            color: #fff;
        }

        .online-count span {
            color: var(--green);
            text-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
        }

        /* STATIC DOT LIVE INDICATOR */
        .live-tag {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 6px 14px;
            border-radius: 20px;
            color: var(--green);
            font-size: 12px;
            font-weight: 700;
        }

        /* STATIC GREEN DOT (NO ANIMATION) */
        .static-dot {
            width: 8px;
            height: 8px;
            background-color: var(--green);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--green);
        }

        .player-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
            gap: 16px;
            overflow-y: auto;
            flex: 1;
            padding-right: 6px;
        }

        .player-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-glass);
            border-radius: 16px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .player-card:hover {
            transform: translateY(-3px);
            border-color: var(--accent);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        }

        .player-card .nickname {
            font-size: 17px;
            font-weight: 800;
            color: #fff;
        }

        .info-row {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: var(--text-muted);
            align-items: center;
        }

        .room-badge {
            background: rgba(239, 68, 68, 0.15);
            color: var(--red);
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 2px 8px;
            border-radius: 6px;
            font-family: monospace;
            font-weight: 700;
        }

        /* History Bubble Near Middle */
        .history-bubble {
            flex: 0.9;
            background: var(--bg-glass);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid var(--border-glass);
            border-radius: 30px;
            padding: 32px;
            height: 90%;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
        }

        .history-bubble h2 {
            font-size: 16px;
            font-weight: 800;
            letter-spacing: 1px;
            margin-bottom: 16px;
            color: #fff;
            text-transform: uppercase;
        }

        .search-box {
            width: 100%;
            padding: 12px 16px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border-glass);
            border-radius: 14px;
            color: #fff;
            outline: none;
            margin-bottom: 16px;
            font-size: 13px;
        }

        .search-box:focus {
            border-color: var(--accent);
        }

        .history-list {
            list-style: none;
            overflow-y: auto;
            flex: 1;
            padding-right: 4px;
        }

        .history-item {
            background: rgba(255, 255, 255, 0.025);
            border: 1px solid var(--border-glass);
            padding: 12px 16px;
            margin-bottom: 10px;
            border-radius: 12px;
            font-size: 12px;
            font-family: monospace;
            word-break: break-all;
            color: #d1d5db;
        }

        .empty-state {
            background: rgba(255, 255, 255, 0.02);
            border: 1px dashed var(--border-glass);
            border-radius: 16px;
            padding: 40px;
            text-align: center;
            color: var(--text-muted);
            grid-column: 1 / -1;
            font-size: 13px;
        }

        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--accent); }
    </style>
</head>
<body>

    <!-- Animated Grid Background -->
    <div class="bg-grid-animation"></div>

    <!-- Big Glowing White Orb in Middle -->
    <div class="white-center-orb"></div>

    <!-- Centered Dashboard Container -->
    <div class="dashboard-container">
        
        <!-- Left Main Panel -->
        <div class="main-card">
            <div class="header-title">FlowMenu Dashboard</div>
            
            <div class="online-banner">
                <div class="online-count">ONLINE: <span id="onlineCount">0</span></div>
                <div class="live-tag">
                    <div class="static-dot"></div> LIVE
                </div>
            </div>

            <div id="activePlayersGrid" class="player-grid">
                <div class="empty-state">No active players online</div>
            </div>
        </div>

        <!-- Right Floating History Bubble -->
        <div class="history-bubble">
            <h2>History</h2>
            <input type="text" id="searchInput" class="search-box" placeholder="Search Player ID..." oninput="filterHistory()">
            
            <ul id="historyList" class="history-list">
                <!-- Populated via JS -->
            </ul>
        </div>

    </div>

    <script>
        let cachedStoredIds = [];

        async function fetchStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('onlineCount').textContent = data.online_count || 0;
                renderActivePlayers(data.players || []);

                const newIds = data.stored_player_ids || [];
                if (JSON.stringify(newIds) !== JSON.stringify(cachedStoredIds)) {
                    cachedStoredIds = newIds;
                    renderHistoryList(cachedStoredIds);
                }
            } catch (err) {
                console.error("Error fetching stats:", err);
            }
        }

        function renderActivePlayers(players) {
            const grid = document.getElementById('activePlayersGrid');
            
            if (players.length === 0) {
                grid.innerHTML = '<div class="empty-state">No active players online</div>';
                return;
            }

            const fragment = document.createDocumentFragment();

            players.forEach(p => {
                const card = document.createElement('div');
                card.className = 'player-card';
                card.innerHTML = `
                    <div class="nickname">${escapeHtml(p.nickname)}</div>
                    <div class="info-row">
                        <span>Room</span>
                        <span class="room-badge">${escapeHtml(p.room)}</span>
                    </div>
                    <div class="info-row">
                        <span>ID</span>
                        <span style="font-family:monospace;">${escapeHtml(p.player_id)}</span>
                    </div>
                `;
                fragment.appendChild(card);
            });

            grid.innerHTML = '';
            grid.appendChild(fragment);
        }

        function renderHistoryList(idArray) {
            const list = document.getElementById('historyList');
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            
            const filtered = idArray.filter(id => id.toLowerCase().includes(searchTerm));

            if (filtered.length === 0) {
                list.innerHTML = '<li class="history-item" style="color:#6b7280; text-align:center;">No IDs found</li>';
                return;
            }

            const fragment = document.createDocumentFragment();

            filtered.forEach(id => {
                const li = document.createElement('li');
                li.className = 'history-item';
                li.textContent = id;
                fragment.appendChild(li);
            });

            list.innerHTML = '';
            list.appendChild(fragment);
        }

        function filterHistory() {
            renderHistoryList(cachedStoredIds);
        }

        function escapeHtml(str) {
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

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
