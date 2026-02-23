from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.projects import router as projects_router
from routers.sse import router as sse_router

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
app.include_router(sse_router, prefix="/api/sse", tags=["sse"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
