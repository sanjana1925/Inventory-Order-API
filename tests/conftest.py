import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_headers(client):
    client.post("/users", json={"email": "admin@test.com", "password": "adminpass123", "role": "admin"})
    resp = client.post("/auth/login", json={"email": "admin@test.com", "password": "adminpass123"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def make_product(client, admin_headers):
    def _make(name="Widget", price=10.0, stock_qty=5):
        resp = client.post(
            "/products", json={"name": name, "price": price, "stock_qty": stock_qty}, headers=admin_headers
        )
        assert resp.status_code == 201
        return resp.json()

    return _make
