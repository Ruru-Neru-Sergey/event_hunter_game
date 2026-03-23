from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import json
import uuid
import random
import redis
from pydantic import BaseModel

app = FastAPI(title="Event Hunter Game", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
try:
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_client.ping()
    print("✅ Connected to Redis")
except:
    print("⚠️  Redis not running, using in-memory storage")
    redis_client = None

# In-memory storage (fallback)
class MemoryStorage:
    def __init__(self):
        self.users = {}
        self.matches = {}
        self.predictions = {}
        self.leaderboard = {}
        
memory_storage = MemoryStorage()

# Models
class UserCreate(BaseModel):
    username: str
    email: str

class UserResponse(BaseModel):
    id: str
    username: str
    score: int
    rank: int

class PredictionRequest(BaseModel):
    user_id: str
    match_id: str
    event_type: str
    predicted_time: float
    confidence: int

class MatchEvent(BaseModel):
    match_id: str
    event_type: str
    actual_time: float
    event_data: Dict[str, Any] = {}

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, match_id: str):
        await websocket.accept()
        if match_id not in self.active_connections:
            self.active_connections[match_id] = []
        self.active_connections[match_id].append(websocket)
        
    def disconnect(self, websocket: WebSocket, match_id: str):
        if match_id in self.active_connections:
            self.active_connections[match_id].remove(websocket)
            
    async def broadcast(self, match_id: str, message: Dict):
        if match_id in self.active_connections:
            for connection in self.active_connections[match_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# Scoring System
def calculate_points(prediction_time: float, actual_time: float, confidence: int) -> int:
    time_diff = abs(prediction_time - actual_time)
    
    if time_diff < 5:
        base_points = 1000
    elif time_diff < 10:
        base_points = 500
    elif time_diff < 30:
        base_points = 200
    elif time_diff < 60:
        base_points = 100
    else:
        base_points = 50
        
    confidence_multiplier = 1 + (confidence / 100)
    time_bonus = max(0, 100 - time_diff) if time_diff < 100 else 0
    
    return int((base_points * confidence_multiplier) + time_bonus)

def update_user_score(user_id: str, points: int):
    if redis_client:
        current = int(redis_client.hget(f"user:{user_id}", "score") or 0)
        new_score = current + points
        redis_client.hset(f"user:{user_id}", "score", new_score)
        redis_client.zadd("leaderboard", {user_id: new_score})
    else:
        if user_id not in memory_storage.users:
            memory_storage.users[user_id] = {"score": 0}
        memory_storage.users[user_id]["score"] += points
        memory_storage.leaderboard[user_id] = memory_storage.users[user_id]["score"]

# API Endpoints
@app.post("/api/users/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    user_id = str(uuid.uuid4())[:8]
    
    if redis_client:
        redis_client.hset(f"user:{user_id}", mapping={
            "username": user.username,
            "email": user.email,
            "score": "0",
            "created_at": datetime.now().isoformat()
        })
    else:
        memory_storage.users[user_id] = {
            "username": user.username,
            "email": user.email,
            "score": 0,
            "created_at": datetime.now().isoformat()
        }
    
    return UserResponse(
        id=user_id,
        username=user.username,
        score=0,
        rank=0
    )

@app.get("/api/leaderboard")
async def get_leaderboard(limit: int = 10):
    leaderboard = []
    
    if redis_client:
        top_users = redis_client.zrevrange("leaderboard", 0, limit-1, withscores=True)
        for idx, (user_id, score) in enumerate(top_users):
            user_data = redis_client.hgetall(f"user:{user_id}")
            leaderboard.append({
                "user_id": user_id,
                "username": user_data.get("username", "Unknown"),
                "score": int(score),
                "rank": idx + 1
            })
    else:
        sorted_users = sorted(memory_storage.leaderboard.items(), key=lambda x: x[1], reverse=True)[:limit]
        for idx, (user_id, score) in enumerate(sorted_users):
            user_data = memory_storage.users.get(user_id, {})
            leaderboard.append({
                "user_id": user_id,
                "username": user_data.get("username", "Unknown"),
                "score": score,
                "rank": idx + 1
            })
    
    return JSONResponse(content={"leaderboard": leaderboard})

@app.get("/api/matches/active")
async def get_active_matches():
    matches_data = []
    
    if redis_client:
        match_ids = redis_client.smembers("active_matches")
        for match_id in match_ids:
            data = redis_client.hgetall(f"match:{match_id}")
            if data:
                matches_data.append({
                    "match_id": match_id,
                    "team_a": data.get("team_a", "Team A"),
                    "team_b": data.get("team_b", "Team B"),
                    "current_time": float(data.get("current_time", 0)),
                    "score": data.get("score", "0-0"),
                    "ai_predictions": [
                        {"event_type": "goal", "predicted_time": random.uniform(300, 900), "confidence": random.randint(60, 95)},
                        {"event_type": "strike", "predicted_time": random.uniform(100, 400), "confidence": random.randint(60, 95)},
                        {"event_type": "foul", "predicted_time": random.uniform(50, 200), "confidence": random.randint(60, 95)}
                    ]
                })
    else:
        if not memory_storage.matches:
            memory_storage.matches = {
                "match_001": {"team_a": "Team Alpha", "team_b": "Team Beta", "current_time": 0, "score": "0-0"},
                "match_002": {"team_a": "Team Gamma", "team_b": "Team Delta", "current_time": 0, "score": "0-0"}
            }
        
        for match_id, data in memory_storage.matches.items():
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

@app.post("/api/predictions")
async def make_prediction(prediction: PredictionRequest):
    prediction_id = str(uuid.uuid4())[:8]
    
    prediction_data = {
        "id": prediction_id,
        "user_id": prediction.user_id,
        "match_id": prediction.match_id,
        "event_type": prediction.event_type,
        "predicted_time": prediction.predicted_time,
        "confidence": prediction.confidence,
        "timestamp": datetime.now().isoformat()
    }
    
    if redis_client:
        redis_client.hset(f"prediction:{prediction_id}", mapping=prediction_data)
        redis_client.expire(f"prediction:{prediction_id}", 300)
        redis_client.sadd(f"match:{prediction.match_id}:predictions", prediction_id)
    else:
        if prediction.match_id not in memory_storage.predictions:
            memory_storage.predictions[prediction.match_id] = []
        memory_storage.predictions[prediction.match_id].append(prediction_data)
    
    return JSONResponse(content={
        "prediction_id": prediction_id,
        "status": "active",
        "message": "Prediction recorded!"
    })

@app.post("/api/events/trigger")
async def trigger_event(event: MatchEvent):
    results = []
    
    if redis_client:
        prediction_ids = redis_client.smembers(f"match:{event.match_id}:predictions")
        for pred_id in prediction_ids:
            pred_data = redis_client.hgetall(f"prediction:{pred_id}")
            if pred_data and pred_data.get("event_type") == event.event_type:
                points = calculate_points(
                    float(pred_data["predicted_time"]),
                    event.actual_time,
                    int(pred_data["confidence"])
                )
                update_user_score(pred_data["user_id"], points)
                results.append({
                    "user_id": pred_data["user_id"],
                    "points": points
                })
                redis_client.delete(f"prediction:{pred_id}")
    else:
        if event.match_id in memory_storage.predictions:
            for pred in memory_storage.predictions[event.match_id]:
                if pred["event_type"] == event.event_type:
                    points = calculate_points(
                        pred["predicted_time"],
                        event.actual_time,
                        pred["confidence"]
                    )
                    update_user_score(pred["user_id"], points)
                    results.append({
                        "user_id": pred["user_id"],
                        "points": points
                    })
            memory_storage.predictions[event.match_id] = []
    
    # Broadcast event
    await manager.broadcast(event.match_id, {
        "type": "event",
        "event_type": event.event_type,
        "actual_time": event.actual_time,
        "results": results
    })
    
    return JSONResponse(content={
        "status": "event_processed",
        "points_awarded": len(results)
    })

@app.websocket("/ws/{match_id}")
async def websocket_endpoint(websocket: WebSocket, match_id: str):
    await manager.connect(websocket, match_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, match_id)

@app.on_event("startup")
async def startup_event():
    # Initialize demo matches
    if redis_client:
        redis_client.delete("active_matches")
        demo_matches = [
            ("match_001", "Team Alpha", "Team Beta"),
            ("match_002", "Team Gamma", "Team Delta"),
        ]
        for match_id, team_a, team_b in demo_matches:
            redis_client.sadd("active_matches", match_id)
            redis_client.hset(f"match:{match_id}", mapping={
                "team_a": team_a,
                "team_b": team_b,
                "score": "0-0",
                "current_time": "0",
                "events_count": "0"
            })
    
    # Start background event generator
    asyncio.create_task(event_generator())

async def event_generator():
    """Auto-generate random events"""
    while True:
        await asyncio.sleep(random.uniform(30, 60))
        
        if redis_client:
            match_ids = redis_client.smembers("active_matches")
        else:
            match_ids = list(memory_storage.matches.keys())
            
        if match_ids:
            match_id = random.choice(list(match_ids))
            event_type = random.choice(["goal", "strike", "foul"])
            
            if redis_client:
                current_time = float(redis_client.hget(f"match:{match_id}", "current_time") or 0)
            else:
                current_time = memory_storage.matches.get(match_id, {}).get("current_time", 0)
                
            current_time += random.uniform(30, 90)
            
            if redis_client:
                redis_client.hset(f"match:{match_id}", "current_time", current_time)
            else:
                if match_id in memory_storage.matches:
                    memory_storage.matches[match_id]["current_time"] = current_time
            
            await trigger_event(MatchEvent(
                match_id=match_id,
                event_type=event_type,
                actual_time=current_time,
                event_data={"auto_generated": True}
            ))

@app.get("/")
async def root():
    return {"message": "Event Hunter Game API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
