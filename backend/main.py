from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.projects import router as projects_router

app = FastAPI(title="Eval Builder API")

# CORS configuration for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
