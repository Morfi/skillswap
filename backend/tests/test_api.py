from .conftest import register

GUITAR = {"kind": "offer", "title": "Гитара", "category": "music", "level": "expert", "format": "both"}
ENGLISH = {"kind": "offer", "title": "Английский язык", "category": "languages", "level": "expert"}


def test_auth_flow(client):
    h = register(client, "a@test.io", "Alice")
    me = client.get("/api/auth/me", headers=h).json()
    assert me["role"] == "user"
    assert client.post("/api/auth/register", json={"email": "a@test.io", "username": "xx", "password": "secret123"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "a@test.io", "password": "wrong"}).status_code == 401
    assert client.get("/api/skills").status_code == 401


def test_skill_crud_and_ownership(client):
    alice, bob = register(client, "a@test.io"), register(client, "b@test.io")
    sid = client.post("/api/skills", json=GUITAR, headers=alice).json()["id"]
    assert client.get(f"/api/skills/{sid}", headers=bob).json()["title"] == "Гитара"
    upd = client.put(f"/api/skills/{sid}", json={**GUITAR, "title": "Электрогитара"}, headers=alice)
    assert upd.json()["title"] == "Электрогитара"
    assert client.put(f"/api/skills/{sid}", json=GUITAR, headers=bob).status_code == 403
    assert client.delete(f"/api/skills/{sid}", headers=bob).status_code == 403
    assert client.delete(f"/api/skills/{sid}", headers=alice).status_code == 204
    assert client.get(f"/api/skills/{sid}", headers=alice).status_code == 404


def test_invalid_category(client):
    h = register(client, "a@test.io")
    assert client.post("/api/skills", json={**GUITAR, "category": "magic"}, headers=h).status_code == 422


def test_mutual_matches(client):
    alice, bob = register(client, "a@test.io", "Alice"), register(client, "b@test.io", "Bob")
    client.post("/api/skills", json=ENGLISH, headers=alice)
    client.post("/api/skills", json={**GUITAR, "kind": "want"}, headers=alice)
    client.post("/api/skills", json=GUITAR, headers=bob)
    client.post("/api/skills", json={**ENGLISH, "kind": "want"}, headers=bob)
    matches = client.get("/api/skills/matches", headers=alice).json()
    assert len(matches) == 1
    assert matches[0]["mutual"] is True
    assert matches[0]["user"]["username"] == "Bob"


def test_exchange_lifecycle(client):
    alice, bob = register(client, "a@test.io", "Alice"), register(client, "b@test.io", "Bob")
    my_skill = client.post("/api/skills", json=ENGLISH, headers=alice).json()["id"]
    bob_skill = client.post("/api/skills", json=GUITAR, headers=bob).json()["id"]

    assert client.post("/api/exchanges", json={"requested_skill_id": my_skill}, headers=alice).status_code == 400
    r = client.post(
        "/api/exchanges",
        json={"requested_skill_id": bob_skill, "offered_skill_id": my_skill, "message": "Привет!"},
        headers=alice,
    )
    assert r.status_code == 201
    ex = r.json()
    assert ex["receiver_name"] == "Bob" and ex["status"] == "pending"
    assert client.post("/api/exchanges", json={"requested_skill_id": bob_skill}, headers=alice).status_code == 409

    eid = ex["id"]
    assert client.put(f"/api/exchanges/{eid}", json={"offered_skill_id": my_skill, "message": "Upd"}, headers=alice).json()["message"] == "Upd"
    assert client.put(f"/api/exchanges/{eid}", json={"message": "x"}, headers=bob).status_code == 403
    assert len(client.get("/api/exchanges?direction=incoming", headers=bob).json()) == 1

    # requester не может принять свою же заявку
    assert client.patch(f"/api/exchanges/{eid}/status", json={"status": "accepted"}, headers=alice).status_code == 403
    assert client.patch(f"/api/exchanges/{eid}/status", json={"status": "accepted"}, headers=bob).json()["status"] == "accepted"
    assert client.post(f"/api/exchanges/{eid}/rate", json={"rating": 5}, headers=alice).status_code == 400
    assert client.delete(f"/api/exchanges/{eid}", headers=alice).status_code == 400
    assert client.patch(f"/api/exchanges/{eid}/status", json={"status": "completed"}, headers=alice).json()["status"] == "completed"
    assert client.post(f"/api/exchanges/{eid}/rate", json={"rating": 5}, headers=alice).status_code == 200
    assert client.post(f"/api/exchanges/{eid}/rate", json={"rating": 4}, headers=alice).status_code == 409

    bob_id = client.get("/api/auth/me", headers=bob).json()["id"]
    assert client.get(f"/api/users/{bob_id}", headers=alice).json()["rating"] == 5


def test_exchange_delete_pending(client):
    alice, bob = register(client, "a@test.io"), register(client, "b@test.io")
    bob_skill = client.post("/api/skills", json=GUITAR, headers=bob).json()["id"]
    eid = client.post("/api/exchanges", json={"requested_skill_id": bob_skill}, headers=alice).json()["id"]
    assert client.delete(f"/api/exchanges/{eid}", headers=bob).status_code == 403
    assert client.delete(f"/api/exchanges/{eid}", headers=alice).status_code == 204
    assert client.get(f"/api/exchanges/{eid}", headers=alice).status_code == 404


def test_admin_permissions(client, admin):
    alice = register(client, "a@test.io")
    assert client.get("/api/admin/users", headers=alice).status_code == 403
    users = client.get("/api/admin/users", headers=admin).json()
    alice_id = next(u["id"] for u in users if u["email"] == "a@test.io")

    sid = client.post("/api/skills", json=GUITAR, headers=alice).json()["id"]
    assert client.delete(f"/api/skills/{sid}", headers=admin).status_code == 204  # модерация

    assert client.patch(f"/api/admin/users/{alice_id}/block", json={"is_blocked": True}, headers=admin).status_code == 200
    assert client.get("/api/auth/me", headers=alice).status_code == 403
    assert client.patch(f"/api/admin/users/{alice_id}/role", json={"role": "admin"}, headers=admin).json()["role"] == "admin"
    assert client.get("/api/admin/stats", headers=admin).json()["users"] == 2
    assert client.delete(f"/api/admin/users/{alice_id}", headers=admin).status_code == 204
