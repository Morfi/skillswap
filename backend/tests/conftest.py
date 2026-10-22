import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SEED_DEMO_DATA"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def register(client, email, name="User"):
    r = client.post("/api/auth/register", json={"email": email, "username": name, "password": "secret123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def admin(client):
    r = client.post("/api/auth/login", json={"email": "admin@skillswap.dev", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
