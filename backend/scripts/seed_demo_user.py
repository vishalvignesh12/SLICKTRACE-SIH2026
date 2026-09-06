"""
Seed the demo user for the Oil Spill Monitoring System.

Usage (from backend/ directory):
    .venv/Scripts/python.exe scripts/seed_demo_user.py

This script uses the backend's own Argon2id hashing (app.core.security)
so the stored hash is always compatible with the login endpoint.

Demo credentials:
    email:    officer.verma@coastguard.gov.in
    password: SIH2026@CoastGuard
    role:     analyst
    name:     Cmdr. Rajesh Verma

NOTE: Alternatively, use the live backend register endpoint:
    POST /api/v1/auth/register
    {"name": "Cmdr. Rajesh Verma", "email": "officer.verma@coastguard.gov.in", "password": "SIH2026@CoastGuard"}
"""

import asyncio
import sys
import os

# Allow running from anywhere inside the backend/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.core.config import settings
from app.core.security import hash_password

# Import all models in dependency order so SQLAlchemy mapper can resolve relationships.
# SpillRegion must be imported before SlickDetection (which has a FK relationship to it).
from app.models.user import User
from app.models.incident import Incident
from app.models.satellite_scene import SatelliteScene
from app.models.spill_region import SpillRegion   # must precede SlickDetection
from app.models.slick_detection import SlickDetection
from app.models.drift_result import DriftResult
from app.models.vessel import Vessel
from app.models.ais_track import AISTrack
from app.models.attribution import AttributionScore
from app.models.inference_log import MLInferenceLog


DEMO_EMAIL    = "officer.verma@coastguard.gov.in"
DEMO_PASSWORD = "SIH2026@CoastGuard"
DEMO_NAME     = "Cmdr. Rajesh Verma"
DEMO_ROLE     = "analyst"


async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check whether the demo user already exists
        stmt = select(User).where(User.email == DEMO_EMAIL)
        result = await session.execute(stmt)
        existing = result.scalars().first()

        if existing:
            print(f"[seed] Demo user already exists: {DEMO_EMAIL} (id={existing.id}) — skipped.")
            await engine.dispose()
            return

        # Hash password with the same Argon2id hasher used by the login endpoint
        pw_hash = hash_password(DEMO_PASSWORD)

        user = User(
            name=DEMO_NAME,
            email=DEMO_EMAIL,
            password_hash=pw_hash,
            role=DEMO_ROLE,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        print(f"[seed] Demo user created successfully.")
        print(f"  id:    {user.id}")
        print(f"  name:  {user.name}")
        print(f"  email: {user.email}")
        print(f"  role:  {user.role}")
        print(f"  hash:  {user.password_hash[:40]}…")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
