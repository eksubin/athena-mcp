from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import answers, applications, health, jobs, profile, resumes, tokens, world
from app.core.config import get_settings

app = FastAPI(title="Athena API", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(profile.router)
app.include_router(resumes.router)
app.include_router(answers.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(world.router)
app.include_router(tokens.router)
