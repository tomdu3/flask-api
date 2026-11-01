def test_user_registration_success(client):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "username": "tester",
            "email": "tester@example.com",
            "password": "SecurePassword1",
        },
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body["user"]["username"] == "tester"
    assert "password_hash" not in body["user"]


def test_user_registration_pydantic_validation_error(client):
    # Invalid email syntax and short/simple password
    res = client.post(
        "/api/v1/auth/register",
        json={"username": "t", "email": "not-an-email", "password": "short"},
    )
    assert res.status_code == 422
    body = res.get_json()
    assert "errors" in body
    assert len(body["errors"]) >= 1


def test_registration_duplicate_username(client):
    payload = {
        "username": "duplicate_user",
        "email": "first@example.com",
        "password": "ValidPassword123",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    payload["email"] = "second@example.com"
    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.get_json()["error"] == "Username already exists"


def test_login_and_protected_route_flow(client):
    # 1. Register
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "curaleaf_dev",
            "email": "dev@curaleaf.com",
            "password": "StrongPassword99",
        },
    )

    # 2. Login via email
    login_res = client.post(
        "/api/v1/auth/login",
        json={"identifier": "dev@curaleaf.com", "password": "StrongPassword99"},
    )
    assert login_res.status_code == 200
    token = login_res.get_json()["token"]

    # 3. Query protected /me endpoint with Bearer token
    me_res = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    assert me_res.get_json()["user"]["username"] == "curaleaf_dev"


def test_protected_route_missing_token(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert "Authorization header is missing" in res.get_json()["error"]


def test_protected_route_invalid_token(client):
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.payload"},
    )
    assert res.status_code == 401
    assert "Invalid authentication token" in res.get_json()["error"]

