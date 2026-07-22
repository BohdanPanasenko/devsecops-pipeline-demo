"""Basic route tests for the demo app (the CI 'test' stage)."""

import pytest

import app as flask_app


@pytest.fixture
def client(tmp_path):
    # Point the app at a throwaway SQLite file and seed it.
    flask_app.DATABASE = str(tmp_path / "test.db")
    flask_app.init_db()
    flask_app.app.config.update(TESTING=True)
    with flask_app.app.test_client() as c:
        yield c


def test_login_page_loads(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Login" in resp.data


def test_items_requires_login(client):
    resp = client.get("/items")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_bad_login_rejected(client):
    resp = client.post("/login", data={"username": "alice", "password": "wrong"})
    assert b"Invalid credentials" in resp.data


def test_good_login_lists_items(client):
    resp = client.post(
        "/login",
        data={"username": "alice", "password": "password123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Laptop" in resp.data       # alice's own item
    assert b"Keyboard" in resp.data     # alice's own item
    assert b"Monitor" not in resp.data  # bob's item must NOT be visible (access control)
