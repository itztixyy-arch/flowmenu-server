import os
import time
import re
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Active player session storage
active_clients = {}
TIMEOUT = 12

# Unique stored player IDs (Prevents duplicate logs)
stored_player_ids = set()

# Maps unique stored IDs -> Nickname (Displayed in History)
stored_history = {}

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
    raw_room = data.get("room_code", "").strip()

    # Normalize room code
    room_code = raw_room if raw_room else "NOT IN ROOM"

    if not player_name or player_name.lower() == "unknown" or re.match(r"^gorilla\d+$", player_name.lower()):
        return jsonify({"status": "ignored", "reason": "unloaded_nickname"}), 200

    # Always track active players on live list (including "NOT IN ROOM")
    active_clients[player_name] = {
        "room": room_code,
        "player_id": player_id if player_id else "Unknown ID",
        "last_seen": time.time()
    }

    # HISTORY CHECK: Store unique ID ONLY after they join a real room
    if room_code.upper() != "NOT IN ROOM" and player_id:
        if player_id not in stored_player_ids:
            stored_player_ids.add(player_id)
            stored_history[player_id] = player_name

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
        "history_nicknames": list(stored_history.values())
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
            --gray-badge: rgba(255, 255, 255, 0.1);
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

        .static-dot {
            width: 8px;
            height: 8px;
            background-color: var(--green);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--green);
        }

        /* ACTIVE PLAYERS STRETCHED LIST */
        .player-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
            overflow-y: auto;
            flex: 1;
            padding-right: 6px;
        }

        .player-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-glass);
            border-radius: 14px;
            padding: 14px 22px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .player-card:hover {
            transform: translateX(3px);
            border-color: var(--accent);
            background: rgba(99, 102, 241, 0.05);
        }

        .player-left {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .player-card .nickname {
            font-size: 22px;
            font-weight: 900;
            color: #fff;
            letter-spacing: -0.5px;
        }

        .player-card .player-id {
            font-size: 11px;
            font-family: monospace;
            color: var(--text-muted);
            opacity: 0.8;
        }

        /* IN-ROOM BADGE */
        .room-badge {
            background: rgba(239, 68, 68, 0.15);
            color: var(--red);
            border: 1px solid rgba(239, 68, 68, 0.35);
            padding: 6px 16px;
            border-radius: 10px;
            font-family: monospace;
            font-weight: 900;
            font-size: 18px;
            letter-spacing: 1px;
        }

        /* NOT IN ROOM BADGE */
        .room-badge.not-in-room {
            background: rgba(156, 163, 175, 0.1);
            color: var(--text-muted);
            border: 1px solid rgba(156, 163, 175, 0.25);
            font-size: 13px;
            font-weight: 700;
        }

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
            font-size: 14px;
            font-weight: 700;
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
            font-size: 13px;
        }

        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--accent); }
    </style>
</head>
<body>

    <div class="bg-grid-animation"></div>

    <div class="dashboard-container">
        
        <div class="main-card">
            <div class="header-title">FlowMenu Dashboard</div>
            
            <div class="online-banner">
                <div class="online-count">ONLINE: <span id="onlineCount">0</span></div>
                <div class="live-tag">
                    <div class="static-dot"></div> LIVE
                </div>
            </div>

            <div id="activePlayersList" class="player-list">
                <div class="empty-state">No active players online</div>
            </div>
        </div>

        <div class="history-bubble">
            <h2>History</h2>
            <input type="text" id="searchInput" class="search-box" placeholder="Search Nicknames..." oninput="filterHistory()">
            
            <ul id="historyList" class="history-list">
                <!-- History Items -->
            </ul>
        </div>

    </div>

    <script>
        let cachedNicknames = [];

        async function fetchStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('onlineCount').textContent = data.online_count || 0;
                renderActivePlayers(data.players || []);

                const newNicks = data.history_nicknames || [];
                if (JSON.stringify(newNicks) !== JSON.stringify(cachedNicknames)) {
                    cachedNicknames = newNicks;
                    renderHistoryList(cachedNicknames);
                }
            } catch (err) {
                console.error("Error fetching stats:", err);
            }
        }

        function renderActivePlayers(players) {
            const list = document.getElementById('activePlayersList');
            
            if (players.length === 0) {
                list.innerHTML = '<div class="empty-state">No active players online</div>';
                return;
            }

            const fragment = document.createDocumentFragment();

            players.forEach(p => {
                const isNotInRoom = !p.room || p.room.toUpperCase() === "NOT IN ROOM";
                const badgeClass = isNotInRoom ? "room-badge not-in-room" : "room-badge";
                const displayRoom = isNotInRoom ? "NOT IN ROOM" : p.room;

                const card = document.createElement('div');
                card.className = 'player-card';
                card.innerHTML = `
                    <div class="player-left">
                        <div class="nickname">${escapeHtml(p.nickname)}</div>
                        <div class="player-id">ID: ${escapeHtml(p.player_id)}</div>
                    </div>
                    <div class="${badgeClass}">${escapeHtml(displayRoom)}</div>
                `;
                fragment.appendChild(card);
            });

            list.innerHTML = '';
            list.appendChild(fragment);
        }

        function renderHistoryList(nicknameArray) {
            const list = document.getElementById('historyList');
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            
            const filtered = nicknameArray.filter(nick => nick.toLowerCase().includes(searchTerm));

            if (filtered.length === 0) {
                list.innerHTML = '<li class="history-item" style="color:#6b7280; text-align:center;">No nicknames logged</li>';
                return;
            }

            const fragment = document.createDocumentFragment();

            filtered.forEach(nick => {
                const li = document.createElement('li');
                li.className = 'history-item';
                li.textContent = nick;
                fragment.appendChild(li);
            });

            list.innerHTML = '';
            list.appendChild(fragment);
        }

        function filterHistory() {
            renderHistoryList(cachedNicknames);
        }

        function escapeHtml(str) {
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        setInterval(fetchStats, 3000);
        fetchStats();
    </script>
</body>
</html>
