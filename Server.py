from flask import Flask, request, jsonify, render_template_string
import time
import re

app = Flask(__name__)

active_clients = {}
TIMEOUT = 12

def cleanup_inactive_players():
    current_time = time.time()
    # Delete expired players
    expired = [name for name, data in active_clients.items() if current_time - data["last_seen"] > TIMEOUT]
    for name in expired:
        del active_clients[name]

    # Force purge any ghost "Unknown" or default gorilla entries if they exist
    ghost_keys = [k for k in active_clients.keys() if k.lower() == "unknown" or re.match(r"^gorilla\d+$", k.lower())]
    for ghost in ghost_keys:
        del active_clients[ghost]

@app.route('/ping', methods=['POST'])
def ping():
    cleanup_inactive_players()
    data = request.get_json(silent=True) or {}
    
    player_name = data.get("player_name", "").strip()
    room_code = data.get("room_code", "NOT IN ROOM")

    # Reject 'Unknown', blank names, or temp gorilla names completely
    if not player_name or player_name.lower() == "unknown" or re.match(r"^gorilla\d+$", player_name.lower()):
        return jsonify({"status": "ignored", "reason": "unloaded_nickname"}), 200

    # Record valid player
    active_clients[player_name] = {
        "room": room_code,
        "last_seen": time.time()
    }

    return jsonify({"status": "ok", "online_count": len(active_clients)}), 200

@app.route('/api/stats', methods=['GET'])
def get_stats():
    cleanup_inactive_players()
    players = [
        {"nickname": name, "room": data["room"]}
        for name, data in active_clients.items()
    ]
    return jsonify({
        "online_count": len(active_clients),
        "players": players
    })

@app.route('/', methods=['GET'])
def dashboard():
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FlowMenu Live Status</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background-color: #0d1117; color: #c9d1d9; margin: 0; padding: 30px; }
            .container { max-width: 700px; margin: 0 auto; }
            .card { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
            .counter-title { font-size: 1.2rem; color: #8b949e; margin: 0; }
            .counter-value { font-size: 3rem; font-weight: bold; color: #2ea043; margin: 5px 0 0 0; }
            h2 { font-size: 1.3rem; border-bottom: 1px solid #30363d; padding-bottom: 10px; margin-top: 0; }
            table { width: 100%; border-collapse: collapse; }
            th, td { text-align: left; padding: 12px; border-bottom: 1px solid #21262d; }
            th { color: #8b949e; font-weight: 600; }
            .room-badge { background-color: #21262d; color: #58a6ff; padding: 4px 8px; border-radius: 6px; font-family: monospace; }
            .no-players { color: #8b949e; font-style: italic; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <p class="counter-title">Current Status</p>
                <div class="counter-value" id="player-count">Online: 0</div>
            </div>

            <div class="card">
                <h2>Active Players & Rooms</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Nickname</th>
                            <th>Room Code</th>
                        </tr>
                    </thead>
                    <tbody id="player-table">
                        <tr><td colspan="2" class="no-players">Loading players...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            async function updateDashboard() {
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();

                    document.getElementById('player-count').innerText = `Online: ${data.online_count}`;

                    const tableBody = document.getElementById('player-table');
                    tableBody.innerHTML = '';

                    if (data.players.length === 0) {
                        tableBody.innerHTML = '<tr><td colspan="2" class="no-players">No players currently online</td></tr>';
                    } else {
                        data.players.forEach(player => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td><strong>${player.nickname}</strong></td>
                                <td><span class="room-badge">${player.room}</span></td>
                            `;
                            tableBody.appendChild(row);
                        });
                    }
                } catch (err) {
                    console.error("Error fetching status:", err);
                }
            }

            setInterval(updateDashboard, 2000);
            updateDashboard();
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
