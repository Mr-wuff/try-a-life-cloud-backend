import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import router as game_router

import world_data.config_loader
import world_data.worlds.modern_city
import world_data.worlds.xianxia
import world_data.worlds.medieval_war
import systems.inventory_sys
import systems.relationship_sys
import systems.achievement_sys
import core.game_session
import core.event_resolver
import core.prompt_builder
import llm.ollama_client
import llm.rag_memory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("LifeSimulator")

def create_app() -> FastAPI:
    app = FastAPI(title="Try A Life API", version="2.0.0")
    
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"❌ Caught a global exception: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "server_error", "detail": str(exc)})

    app.include_router(game_router, prefix="/api", tags=["GameFlow"])
    logger.info("✅ Game router module successfully mounted!")

    @app.get("/")
    async def health_check():
        return {"status": "online"}

    return app

app = create_app()

if __name__ == "__main__":
    logger.info("🚀 Starting Try A Life API server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)