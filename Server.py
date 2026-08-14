import time
import threading
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Dictionary to store active clients: { player_name: {"last_seen": timestamp, "room": room_code} }
active_clients = {}
TIMEOUT_SECONDS = 15

def check_timeouts():
    while True:
        time.sleep(5)
        current_time = time.time()
        disconnected_players = []

        for player_name, data in list(active_clients.items()):
            if current_time - data["last_seen"] > TIMEOUT_SECONDS:
                disconnected_players.append(player_name)

        for player_name in disconnected_players:
            last_room = active_clients[player_name]["room"]
            del active_clients[player_name]
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            total_players = len(active_clients)
            
            print(f"[{timestamp}] ❌ LEFT  | Player: {player_name} | Room: {last_room} | Online: {total_players}")

@app.route('/ping', methods=['POST'])
def receive_ping():
    data = request.json
    if data:
        player_name = data.get('player', 'Unknown')
        room_code = data.get('room', 'Unknown')
        current_time = time.time()

        timestamp = datetime.now().strftime('%H:%M:%S')

        if player_name not in active_clients:
            active_clients[player_name] = {
                "last_seen": current_time,
                "room": room_code
            }
            total_players = len(active_clients)
            print(f"[{timestamp}] 🟢 JOIN  | Player: {player_name} | Room: {room_code} | Online: {total_players}")
        else:
            # Update timestamp and room silently if they change lobbies
            active_clients[player_name]["last_seen"] = current_time
            active_clients[player_name]["room"] = room_code

        return jsonify({"status": "ok", "online_count": len(active_clients)}), 200

    return jsonify({"status": "bad request"}), 400

if __name__ == '__main__':
    tracker_thread = threading.Thread(target=check_timeouts, daemon=True)
    tracker_thread.start()

    app.run(host='0.0.0.0', port=5000)