from fastapi import FastAPI

from services.api.app.routers import agent_runs, chapters, events, local_rewrites, projects


def create_app() -> FastAPI:
    app = FastAPI(title="Novel Gen API")
    app.include_router(projects.router)
    app.include_router(chapters.router)
    app.include_router(agent_runs.router)
    app.include_router(local_rewrites.router)
    app.include_router(events.router)

    @app.get("/health", tags=["health"])
    def health_check():
        return {"status": "ok"}

    return app


app = create_app()
