import json
import random
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Хранилище данных
users = {}
matches = {
    "match_001": {"team_a": "Team Alpha", "team_b": "Team Beta", "score": "0-0", "current_time": 0},
    "match_002": {"team_a": "Team Gamma", "team_b": "Team Delta", "score": "0-0", "current_time": 0}
}
predictions = []
leaderboard = {}

class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/':
            self.send_json({"status": "running", "message": "Event Hunter Game API"})
        
        elif parsed.path == '/api/matches/active':
            matches_data = []
            for match_id, data in matches.items():
                matches_data.append({
                    "match_id": match_id,
                    "team_a": data["team_a"],
                    "team_b": data["team_b"],
                    "current_time": data["current_time"],
                    "score": data["score"],
                    "ai_predictions": [
                        {"event_type": "goal", "predicted_time": random.uniform(300, 900), "confidence": random.randint(60, 95)},
                        {"event_type": "strike", "predicted_time": random.uniform(100, 400), "confidence": random.randint(60, 95)},
                        {"event_type": "foul", "predicted_time": random.uniform(50, 200), "confidence": random.randint(60, 95)}
                    ]
                })
            self.send_json({"matches": matches_data})
        
        elif parsed.path == '/api/leaderboard':
            sorted_users = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)[:10]
            result = []
            for idx, (user_id, score) in enumerate(sorted_users):
                user_data = users.get(user_id, {})
                result.append({
                    "user_id": user_id,
                    "username": user_data.get("username", "Unknown"),
                    "score": score,
                    "rank": idx + 1
                })
            self.send_json({"leaderboard": result})
        
        else:
            self.send_json({"error": "Not found"}, 404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body)
        except:
            data = {}
        
        parsed = urlparse(self.path)
        
        if parsed.path == '/api/users/register':
            user_id = str(uuid.uuid4())[:8]
            users[user_id] = {
                "username": data.get("username", "Unknown"),
                "email": data.get("email", ""),
                "score": 0
            }
            leaderboard[user_id] = 0
            self.send_json({"id": user_id, "username": data.get("username"), "score": 0, "rank": 0})
        
        elif parsed.path == '/api/predictions':
            pred_id = str(uuid.uuid4())[:8]
            prediction = {
                "id": pred_id,
                "user_id": data.get("user_id"),
                "match_id": data.get("match_id"),
                "event_type": data.get("event_type"),
                "predicted_time": data.get("predicted_time"),
                "confidence": data.get("confidence")
            }
            predictions.append(prediction)
            self.send_json({"prediction_id": pred_id, "status": "active"})
        
        elif parsed.path == '/api/events/trigger':
            match_id = data.get("match_id")
            event_type = data.get("event_type")
            actual_time = data.get("actual_time")
            
            results = []
            for pred in predictions[:]:
                if pred.get("match_id") == match_id and pred.get("event_type") == event_type:
                    time_diff = abs(pred["predicted_time"] - actual_time)
                    if time_diff < 5:
                        points = 1000
                    elif time_diff < 10:
                        points = 500
                    elif time_diff < 30:
                        points = 200
                    else:
                        points = 50
                    
                    points = int(points * (1 + pred["confidence"] / 100))
                    
                    if pred["user_id"] in leaderboard:
                        leaderboard[pred["user_id"]] += points
                        if pred["user_id"] in users:
                            users[pred["user_id"]]["score"] = leaderboard[pred["user_id"]]
                    
                    results.append({"user_id": pred["user_id"], "points": points})
                    predictions.remove(pred)
            
            self.send_json({"status": "processed", "points_awarded": len(results)})
        
        else:
            self.send_json({"error": "Not found"}, 404)

print("=" * 50)
print("🚀 Event Hunter Game Backend")
print("📍 Server: http://localhost:8000")
print("📡 API: http://localhost:8000/api/matches/active")
print("=" * 50)
print("Press Ctrl+C to stop")
print()

server = HTTPServer(('0.0.0.0', 8000), Handler)
server.serve_forever()
