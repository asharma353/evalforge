from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.generation import router as generation_router
from routers.projects import router as projects_router
from routers.questions import router as questions_router
from routers.sse import router as sse_router

app = FastAPI(title="Eval Builder API")

# CORS configuration for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3010"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(questions_router, prefix="/api/projects/questions", tags=["questions"])
app.include_router(generation_router, prefix="/api/projects", tags=["generation"])
app.include_router(sse_router, prefix="/api/sse", tags=["sse"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
