from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import random
import uuid
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище в памяти
users = {}
matches = {
    "match_001": {"team_a": "Team Alpha", "team_b": "Team Beta", "score": "0-0", "current_time": 0},
    "match_002": {"team_a": "Team Gamma", "team_b": "Team Delta", "score": "0-0", "current_time": 0}
}
predictions = []
leaderboard = {}

class UserCreate(BaseModel):
    username: str
    email: str

@app.get("/")
async def root():
    return {"status": "running", "message": "Event Hunter Game API"}

@app.get("/api/matches/active")
async def get_matches():
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
    return JSONResponse(content={"matches": matches_data})

@app.post("/api/users/register")
async def register(user: UserCreate):
    user_id = str(uuid.uuid4())[:8]
    users[user_id] = {
        "username": user.username,
        "email": user.email,
        "score": 0,
        "created_at": datetime.now().isoformat()
    }
    leaderboard[user_id] = 0
    return JSONResponse(content={"id": user_id, "username": user.username, "score": 0, "rank": 0})

@app.get("/api/leaderboard")
async def get_leaderboard():
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
    return JSONResponse(content={"leaderboard": result})

@app.post("/api/predictions")
async def make_prediction(data: dict):
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
    return JSONResponse(content={"prediction_id": pred_id, "status": "active"})

@app.post("/api/events/trigger")
async def trigger_event(data: dict):
    match_id = data.get("match_id")
    event_type = data.get("event_type")
    actual_time = data.get("actual_time")
    
    results = []
    for pred in predictions[:]:
        if pred["match_id"] == match_id and pred["event_type"] == event_type:
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
    
    return JSONResponse(content={"status": "processed", "points_awarded": len(results)})

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting backend on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
