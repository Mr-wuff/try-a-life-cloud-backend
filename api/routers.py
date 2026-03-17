import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from .schemas import StartGameRequest, NormalChoiceRequest, NodeChoiceRequest

try:
    from core.game_session import GameSession
    from world_data.config_loader import load_world_config
    from llm.cloud_client import CloudLLMBackend
    from systems.inventory_sys import InventorySystem
    from systems.achievement_sys import AchievementSystem
except ImportError:
    pass

logger = logging.getLogger("LifeSimulator.API")
router = APIRouter()

class SessionManager:
    def __init__(self):
        self.session = None
        try:
            # Use Cloud LLM engine by default
            self.llm_backend = CloudLLMBackend()
        except Exception as e:
            logger.error(f"Cloud LLM initialization failed: {e}")
            self.llm_backend = None

manager = SessionManager()

# =========================================================
# 1. Status & LLM Management API (For Godot menu connection checks)
# =========================================================

@router.get("/status", summary="Get server and model status")
async def get_status():
    model_name = "Cloud / Custom API"
    if manager.llm_backend and hasattr(manager.llm_backend, "model_name"):
        model_name = manager.llm_backend.model_name
    return {"status": "online", "model": model_name}

@router.get("/model_catalog", summary="Get model catalog")
async def get_model_catalog():
    return {
        "current_model": "Cloud API (Render)",
        "catalog": [
            {
                "name": "Cloud API (Render)",
                "id": "cloud_api",
                "description": "Cloud LLM service hosted on Render, powered by OpenRouter.",
                "size": "N/A", "vram": "0GB", "speed": "Fast", "quality": "High",
                "installed": True, "tier": "recommended"
            }
        ]
    }

# =========================================================
# 2. Virtual/Mock APIs (Compatibility for Godot frontend)
# =========================================================

class PullModelRequest(BaseModel):
    model: str

@router.post("/pull_model")
async def pull_model(req: PullModelRequest):
    return {"status": "error", "error": "Cloud mode does not need to pull local models."}

@router.get("/pull_progress")
async def pull_progress(model: str = ""):
    return {"status": "error", "error": "This feature is not supported in cloud mode."}

class SwitchModelRequest(BaseModel):
    model: str

@router.post("/switch_model")
async def switch_model(req: SwitchModelRequest):
    return {"status": "success"}

class CustomAPIRequest(BaseModel):
    url: str
    key: str
    model: str

@router.post("/set_custom_api")
async def set_custom_api(req: CustomAPIRequest):
    if manager.llm_backend:
        manager.llm_backend.base_url = req.url
        manager.llm_backend.api_key = req.key
        manager.llm_backend.model_name = req.model
    return {"status": "success"}

# =========================================================
# 3. Core Game Flow APIs
# =========================================================

@router.post("/start_game", summary="Initialize a new life")
async def start_game(req: StartGameRequest):
    try:
        world_config = load_world_config(req.world_key)
        manager.session = GameSession(
            llm=manager.llm_backend, 
            world_config=world_config, 
            char_name=req.character_name, 
            gender=req.gender,             
            difficulty=req.difficulty,     
            stats=req.stats
        )
        return {"status": "success", "age": manager.session.age, "world_name": manager.session.world_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get_state", summary="Get current character state")
async def get_state():
    if not manager.session: 
        raise HTTPException(status_code=400, detail="Game not initialized.")
    return {
        "character_name": manager.session.character_name,
        "world_name": manager.session.world_name,
        "age": manager.session.age,
        "stats": manager.session.stats,
        "is_dead": manager.session.is_dead,
        "cause_of_death": manager.session.cause_of_death,
        "inventory": InventorySystem.get_inventory_list(manager.session) if hasattr(InventorySystem, "get_inventory_list") else [],
        "causal_tags": manager.session.causal_tags
    }

@router.get("/generate_event", summary="Generate next year's event")
async def generate_event():
    if not manager.session: raise HTTPException(status_code=400, detail="Game not initialized.")
    if manager.session.is_dead: raise HTTPException(status_code=400, detail="Character is already dead.")
    return manager.session.generate_next_event()

@router.post("/submit_normal_choice", summary="Submit normal event choice")
async def submit_normal_choice(req: NormalChoiceRequest):
    if not manager.session: raise HTTPException(status_code=400, detail="Game not initialized.")
    result = manager.session.resolve_normal_choice(req.choice_index)
    manager.session.current_event_data = None 
    return result

@router.post("/submit_node_choice", summary="Submit node event investments")
async def submit_node_choice(req: NodeChoiceRequest):
    if not manager.session: raise HTTPException(status_code=400, detail="Game not initialized.")
    result = manager.session.submit_node_investments(req.investments)
    return result

@router.post("/resolve_node_narrative", summary="Resolve deep narrative for node event")
async def resolve_node_narrative():
    if not manager.session: raise HTTPException(status_code=400, detail="Game not initialized.")
    result = manager.session.resolve_node_narrative()
    manager.session.current_event_data = None
    return result

@router.get("/get_leaderboard", summary="Get leaderboard data")
async def get_leaderboard():
    try:
        data = AchievementSystem.get_leaderboard()
        return {"status": "success", "data": data}
    except Exception:
        return {"status": "success", "data": []}

class LeaderboardRequest(BaseModel):
    epic_ending: str

@router.post("/submit_leaderboard", summary="Submit epic player record")
async def submit_leaderboard(req: LeaderboardRequest):
    if manager.session:
        try:
            score = AchievementSystem.calculate_score(manager.session)
            AchievementSystem.save_to_leaderboard(
                manager.session.character_name,
                score,
                req.epic_ending,
                manager.session.age,
                manager.session.world_name
            )
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    return {"status": "error", "error": "No valid session found."}
