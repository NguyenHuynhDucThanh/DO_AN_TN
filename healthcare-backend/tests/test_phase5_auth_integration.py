"""Phase 5 cookie/JWT authentication, CSRF, rotation, and RBAC integration tests."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password
from app.auth.tokens import create_access_token, hash_refresh_token
from app.core.config import get_settings
from app.core.database import get_db
from app.main import create_app
from app.models.enums import UserStatus
from app.models.identity import RefreshSession, Role, User, UserRole
from app.models.medical_record import MedicalRecord

pytestmark = pytest.mark.integration
ORIGIN = "http://localhost:5173"
PASSWORD = "DemoPass123"


@pytest.fixture
def phase5_session(real_database):
    connection = real_database.connect()
    outer_transaction = connection.begin()
    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture
def phase5_app(phase5_session: Session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", "phase5-test-secret-that-is-longer-than-32-characters")
    monkeypatch.setenv("FRONTEND_ORIGIN", ORIGIN)
    monkeypatch.setenv("DEV_AUTH_ENABLED", "true")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: phase5_session
    yield app
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
async def phase5_client(phase5_app):
    async with AsyncClient(
        transport=ASGITransport(app=phase5_app), base_url="http://testserver"
    ) as client:
        yield client


def registration_payload(email: str | None = None) -> dict[str, str]:
    return {
        "email": email or f"patient.{uuid4().hex[:10]}@example.com",
        "password": PASSWORD,
        "full_name": "Patient Synthetic",
        "phone": "0900000098",
    }


async def register(client: AsyncClient, email: str | None = None):
    return await client.post(
        "/api/v1/auth/register",
        json=registration_payload(email),
        headers={"Origin": ORIGIN},
    )


def csrf_header(client: AsyncClient, *, origin: str = ORIGIN) -> dict[str, str]:
    csrf_token = client.cookies.get("healthcare_csrf")
    assert csrf_token
    return {"Origin": origin, "X-CSRF-Token": csrf_token}


def create_login_user(session: Session, role_code: str, email: str) -> User:
    role = session.scalar(select(Role).where(Role.code == role_code))
    assert role is not None
    user = User(
        email=email,
        password_hash=hash_password(PASSWORD),
        full_name=f"{role_code} Synthetic",
        phone="0900000097",
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()
    session.add(UserRole(user_id=user.id, role_id=role.id))
    session.commit()
    return user


@pytest.mark.anyio
async def test_register_hashes_password_requires_phone_and_rejects_duplicate_email(
    phase5_client: AsyncClient, phase5_session: Session
) -> None:
    missing_phone = registration_payload()
    missing_phone.pop("phone")
    assert (
        await phase5_client.post(
            "/api/v1/auth/register", json=missing_phone, headers={"Origin": ORIGIN}
        )
    ).status_code == 422

    email = f"case.{uuid4().hex[:10]}@example.com"
    created = await register(phase5_client, email)
    assert created.status_code == 201
    assert created.json()["user"]["roles"] == ["PATIENT"]
    assert created.json()["user"]["phone"] == "0900000098"
    set_cookies = created.headers.get_list("set-cookie")
    assert any("healthcare_access=" in cookie and "HttpOnly" in cookie for cookie in set_cookies)
    assert any("healthcare_refresh=" in cookie and "HttpOnly" in cookie for cookie in set_cookies)
    assert any("healthcare_csrf=" in cookie and "HttpOnly" not in cookie for cookie in set_cookies)

    user = phase5_session.scalar(select(User).where(User.email == email))
    assert user is not None
    assert user.password_hash.startswith("$argon2")
    assert PASSWORD not in user.password_hash

    duplicate = await register(phase5_client, email.upper())
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_exists"


@pytest.mark.anyio
async def test_login_is_case_insensitive_rejects_invalid_password_and_inactive_user(
    phase5_client: AsyncClient, phase5_session: Session
) -> None:
    email = f"login.{uuid4().hex[:10]}@example.com"
    assert (await register(phase5_client, email)).status_code == 201
    invalid = await phase5_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPass123"},
        headers={"Origin": ORIGIN},
    )
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "invalid_credentials"

    valid = await phase5_client.post(
        "/api/v1/auth/login",
        json={"email": email.upper(), "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert valid.status_code == 200

    user = phase5_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.status = UserStatus.INACTIVE
    phase5_session.commit()
    inactive = await phase5_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert inactive.status_code == 401
    assert inactive.json()["error"]["code"] == "inactive_user"


@pytest.mark.anyio
async def test_access_cookie_csrf_origin_and_role_authorization(
    phase5_client: AsyncClient,
) -> None:
    anonymous = await phase5_client.get("/api/v1/appointments")
    assert anonymous.status_code == 401
    assert (await register(phase5_client)).status_code == 201
    assert (await phase5_client.get("/api/v1/auth/me")).status_code == 200

    payload = {"reason": "Synthetic support request", "priority": "NORMAL", "source": "USER"}
    missing_csrf = await phase5_client.post(
        "/api/v1/handoffs", json=payload, headers={"Origin": ORIGIN}
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == "csrf_failed"
    wrong_origin = await phase5_client.post(
        "/api/v1/handoffs",
        json=payload,
        headers=csrf_header(phase5_client, origin="https://attacker.example"),
    )
    assert wrong_origin.status_code == 403
    assert wrong_origin.json()["error"]["code"] == "invalid_origin"
    accepted = await phase5_client.post(
        "/api/v1/handoffs", json=payload, headers=csrf_header(phase5_client)
    )
    assert accepted.status_code == 201

    updated = await phase5_client.patch(
        "/api/v1/users/me",
        json={"full_name": "Patient Updated"},
        headers=csrf_header(phase5_client),
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Patient Updated"
    phone_required = await phase5_client.patch(
        "/api/v1/users/me",
        json={"phone": None},
        headers=csrf_header(phase5_client),
    )
    assert phone_required.status_code == 400
    assert phone_required.json()["error"]["code"] == "patient_phone_required"

    forbidden = await phase5_client.post(
        "/api/v1/specialties",
        json={"code": f"AUTH_{uuid4().hex[:8]}", "name": "Auth test specialty"},
        headers=csrf_header(phase5_client),
    )
    assert forbidden.status_code == 403


@pytest.mark.anyio
async def test_refresh_rotates_hashes_and_revokes_family_on_reuse(
    phase5_client: AsyncClient, phase5_session: Session, phase5_app
) -> None:
    assert (await register(phase5_client)).status_code == 201
    old_refresh = phase5_client.cookies.get("healthcare_refresh")
    assert old_refresh
    rotated = await phase5_client.post(
        "/api/v1/auth/refresh", headers=csrf_header(phase5_client)
    )
    assert rotated.status_code == 200
    new_refresh = phase5_client.cookies.get("healthcare_refresh")
    assert new_refresh and new_refresh != old_refresh

    old_session = phase5_session.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == hash_refresh_token(old_refresh)
        )
    )
    assert old_session is not None
    assert old_session.revoked_at is not None
    assert old_session.replaced_by_session_id is not None

    current_csrf = phase5_client.cookies.get("healthcare_csrf")
    assert current_csrf
    async with AsyncClient(
        transport=ASGITransport(app=phase5_app),
        base_url="http://testserver",
        cookies={"healthcare_refresh": old_refresh, "healthcare_csrf": current_csrf},
    ) as reuse_client:
        reuse = await reuse_client.post(
            "/api/v1/auth/refresh",
            headers={"Origin": ORIGIN, "X-CSRF-Token": current_csrf},
        )
    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "refresh_token_reuse"
    replacement = phase5_session.get(RefreshSession, old_session.replaced_by_session_id)
    assert replacement is not None and replacement.revoked_at is not None


@pytest.mark.anyio
async def test_logout_revokes_refresh_session_and_clears_cookies(
    phase5_client: AsyncClient, phase5_session: Session, phase5_app
) -> None:
    assert (await register(phase5_client)).status_code == 201
    raw_refresh = phase5_client.cookies.get("healthcare_refresh")
    old_csrf = phase5_client.cookies.get("healthcare_csrf")
    assert raw_refresh and old_csrf
    logged_out = await phase5_client.post(
        "/api/v1/auth/logout", headers=csrf_header(phase5_client)
    )
    assert logged_out.status_code == 204
    stored = phase5_session.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == hash_refresh_token(raw_refresh)
        )
    )
    assert stored is not None and stored.revoked_at is not None
    assert phase5_client.cookies.get("healthcare_access") is None
    assert phase5_client.cookies.get("healthcare_refresh") is None
    async with AsyncClient(
        transport=ASGITransport(app=phase5_app),
        base_url="http://testserver",
        cookies={"healthcare_refresh": raw_refresh, "healthcare_csrf": old_csrf},
    ) as revoked_client:
        revoked = await revoked_client.post(
            "/api/v1/auth/refresh",
            headers={"Origin": ORIGIN, "X-CSRF-Token": old_csrf},
        )
    assert revoked.status_code == 401
    assert revoked.json()["error"]["code"] == "revoked_session"


@pytest.mark.anyio
async def test_expired_or_invalid_jwt_never_falls_back_to_dev_header(
    phase5_client: AsyncClient, phase5_session: Session
) -> None:
    patient = create_login_user(
        phase5_session, "PATIENT", f"jwt.{uuid4().hex[:10]}@example.com"
    )
    settings = get_settings()
    expired = create_access_token(
        patient.id,
        settings=settings,
        now=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    phase5_client.cookies.set(
        settings.access_cookie_name, expired, path="/api/v1"
    )
    response = await phase5_client.get(
        "/api/v1/appointments", headers={"X-Dev-User-Id": str(patient.id)}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.anyio
async def test_real_auth_preserves_medical_record_object_privacy(
    phase5_session: Session, phase5_app
) -> None:
    record_id = phase5_session.scalar(select(MedicalRecord.id).limit(1))
    assert record_id is not None
    patient = phase5_session.scalar(
        select(User).where(User.email == "patient.lan@example.invalid")
    )
    staff = phase5_session.scalar(
        select(User).where(User.email == "staff.demo@example.invalid")
    )
    assert patient is not None and staff is not None
    patient.password_hash = hash_password(PASSWORD)
    staff.password_hash = hash_password(PASSWORD)
    phase5_session.commit()

    async def clinical_status(email: str) -> int:
        async with AsyncClient(
            transport=ASGITransport(app=phase5_app), base_url="http://testserver"
        ) as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": PASSWORD},
                headers={"Origin": ORIGIN},
            )
            assert login.status_code == 200
            return (await client.get(f"/api/v1/medical-records/{record_id}")).status_code

    assert await clinical_status(patient.email) == 200
    assert await clinical_status(staff.email) == 403

    wrong_patient_email = f"wrong.{uuid4().hex[:10]}@example.com"
    async with AsyncClient(
        transport=ASGITransport(app=phase5_app), base_url="http://testserver"
    ) as client:
        assert (await register(client, wrong_patient_email)).status_code == 201
        assert (await client.get(f"/api/v1/medical-records/{record_id}")).status_code == 403


@pytest.mark.anyio
async def test_dev_header_is_disabled_in_production(
    phase5_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    patient = phase5_session.scalar(
        select(User).where(User.email == "patient.lan@example.invalid")
    )
    assert patient is not None
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "production-test-secret-that-is-longer-than-32-characters")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://frontend.example")
    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: phase5_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://testserver"
    ) as client:
        response = await client.get(
            "/api/v1/appointments", headers={"X-Dev-User-Id": str(patient.id)}
        )
    assert response.status_code == 401
    app.dependency_overrides.clear()
    get_settings.cache_clear()
