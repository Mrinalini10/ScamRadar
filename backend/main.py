"""
ScamRadar FastAPI Backend
Scam Genomic Surveillance System
"""
import os
import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from models.database import init_db
from api import complaints, lineages, alerts, audit, crossbank, admin, dashboard, dataset

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, reload LSH index from existing lineages."""
    print("🚀 ScamRadar starting up...")
    await init_db()
    print("✅ Database initialized")

    # Reload LSH index from DB so lineage assignment works after restart
    from models.database import AsyncSessionLocal
    from models.db_models import Lineage
    from sqlalchemy import select
    from ml.lineage import register_lineage_in_lsh, get_or_create_profile

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Lineage))
        existing_lineages = result.scalars().all()
        for l in existing_lineages:
            if l.act_sequence:
                register_lineage_in_lsh(l.id, l.act_sequence)
                get_or_create_profile(l.id, l.act_sequence)
        print(f"✅ LSH index reloaded: {len(existing_lineages)} lineages")

    yield
    print("🛑 ScamRadar shutting down")


app = FastAPI(
    title="ScamRadar API",
    description="Scam Genomic Surveillance System — tracks fraud campaign lineages like pathogens",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow React dev server
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(complaints.router, prefix="/api/complaints", tags=["Complaints"])
app.include_router(lineages.router, prefix="/api/lineages", tags=["Lineages"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
app.include_router(crossbank.router, prefix="/api/crossbank", tags=["Cross-Bank"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(dataset.router, prefix="/api/dataset", tags=["Dataset"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ScamRadar", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
