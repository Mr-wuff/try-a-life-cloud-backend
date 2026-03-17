import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routers import router as game_router
import world_data.config_loader
import systems.inventory_sys
import systems.relationship_sys
import systems.achievement_sys
import core.game_session
import core.event_resolver
import core.prompt_builder
import llm.cloud_client
import llm.rag_memory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("LifeSimulator")

def create_app() -> FastAPI:
    app = FastAPI(title="Try A Life API (Cloud)", version="2.0.0")
    
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"❌ Caught a global exception: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "server_error", "detail": str(exc)})


    app.include_router(game_router, prefix="/api", tags=["GameFlow"])
    logger.info("✅ The game routing module has been successfully mounted！")


    @app.get("/")
    async def root_welcome():
        return {
            "message": "Welcome to the Cloud Engine of 《Try A Life》！", 
            "status": "online",
            "docs_url": "/docs" # Inform the players where to view the interface documentation
        }

    return app

app = create_app()

if __name__ == "__main__":
    logger.info("🚀 The server for the Try A Life is being ignited and started....")
    uvicorn.run(app, host="0.0.0.0", port=8000)
