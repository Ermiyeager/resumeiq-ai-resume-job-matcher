"""Stage 2: accounts, saved data, analysis history and privacy."""

import re

import pytest

from .conftest import load

PASSWORD = "correct-horse-battery"


def register(client, email="ana@example.com", password=PASSWORD):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Ana"})
    assert r.status_code == 201, r.text
    return r.json()


def upload_resume(client, fixture="resume_call_agent.txt"):
    files = {"file": (fixture, load(fixture).encode(), "text/plain")}
    r = client.post("/api/v1/resumes/upload", files=files, data={"name": "Support CV"})
    assert r.status_code == 201, r.text
    return r.json()


def save_job(client, fixture="job_customer_support.txt"):
    r = client.post("/api/v1/jobs", json={"description": load(fixture), "company_name": "Acme"})
    assert r.status_code == 201, r.text
    return r.json()


def token_from(mailer, purpose):
    body = mailer.sent[-1][2]
    return re.search(rf"{purpose}\?token=([\w-]+)", body).group(1)


@pytest.fixture
def ana(api_client):
    client = api_client()
    register(client)
    return client


# ------------------------------------------------------------------- auth


def test_register_login_me_logout(api_client):
    client = api_client()
    user = register(client, email="  Ana@Example.com ")
    assert user["email"] == "ana@example.com"
    assert user["email_verified"] is False
    assert client.get("/api/v1/auth/me").status_code == 200

    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401

    r = client.post("/api/v1/auth/login", json={"email": "ana@example.com", "password": PASSWORD})
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me").json()["email"] == "ana@example.com"


def test_session_cookie_is_http_only(api_client):
    client = api_client()
    r = client.post("/api/v1/auth/register", json={"email": "c@example.com", "password": PASSWORD})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_wrong_password_and_unknown_email_look_the_same(api_client):
    client = api_client()
    register(client)
    a = client.post("/api/v1/auth/login", json={"email": "ana@example.com", "password": "wrong-password-1"})
    b = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-password-1"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_weak_password_and_duplicate_email_rejected(api_client):
    client = api_client()
    r = client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "short"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "WEAK_PASSWORD"
    register(client, email="a@example.com")
    r = api_client().post("/api/v1/auth/register", json={"email": "a@example.com", "password": PASSWORD})
    assert r.status_code == 409


def test_passwords_are_hashed(api_client):
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.db_models import User

    register(api_client())
    with SessionLocal() as s:
        user = s.scalar(select(User))
        assert PASSWORD not in user.password_hash
        assert user.password_hash.startswith("$argon2")


def test_email_verification(ana):
    token = token_from(ana.mailer, "verify-email")
    r = ana.post("/api/v1/auth/verify-email", json={"token": token})
    assert r.json()["email_verified"] is True
    # tokens are single-use
    assert ana.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 400


def test_password_reset_logs_out_everywhere(ana, api_client):
    other = api_client()
    other.post("/api/v1/auth/forgot-password", json={"email": "ana@example.com"})
    token = token_from(other.mailer, "reset-password")
    r = other.post("/api/v1/auth/reset-password", json={"token": token, "password": "a-brand-new-passphrase"})
    assert r.status_code == 200
    assert ana.get("/api/v1/auth/me").status_code == 401  # old session revoked
    r = other.post("/api/v1/auth/login", json={"email": "ana@example.com", "password": "a-brand-new-passphrase"})
    assert r.status_code == 200


def test_forgot_password_does_not_reveal_accounts(api_client):
    client = api_client()
    r = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert client.mailer.sent == []


# --------------------------------------------------- scenario A: full flow


def test_full_analysis_flow(ana):
    resume = upload_resume(ana)
    assert resume["latest_version"]["version_number"] == 1
    assert "Customer service" in resume["latest_version"]["parsed_summary"]["skills"]
    assert "storage_key" not in resume

    job = save_job(ana)
    assert job["category"] == "customer_service"
    assert job["keyword_count"] > 5

    r = ana.post("/api/v1/analyses", json={"resume_id": resume["id"], "job_id": job["id"]})
    assert r.status_code == 202
    analysis = ana.get(f"/api/v1/analyses/{r.json()['id']}").json()
    assert analysis["status"] == "COMPLETED"
    assert 0 < analysis["overall_score"] <= 100
    assert analysis["report"]["keyword_matches"]
    assert analysis["resume_name"] == "Support CV"

    history = ana.get("/api/v1/analyses").json()
    assert history["total"] == 1 and history["items"][0]["job_title"]


def test_resume_versions_and_analysis_of_a_specific_version(ana):
    resume = upload_resume(ana)
    job = save_job(ana)
    edited = load("resume_call_agent.txt") + "\nSkills\nActive listening, communication, professionalism, patience"
    r = ana.post(f"/api/v1/resumes/{resume['id']}/versions", json={"text": edited, "note": "Added soft skills"})
    assert r.status_code == 201 and r.json()["version_number"] == 2
    versions = ana.get(f"/api/v1/resumes/{resume['id']}/versions").json()
    assert [v["version_number"] for v in versions] == [2, 1]

    v1 = versions[1]["id"]
    a1 = ana.post("/api/v1/analyses", json={"resume_id": resume["id"], "job_id": job["id"],
                                            "resume_version_id": v1}).json()
    a2 = ana.post("/api/v1/analyses", json={"resume_id": resume["id"], "job_id": job["id"]}).json()
    s1 = ana.get(f"/api/v1/analyses/{a1['id']}").json()["overall_score"]
    s2 = ana.get(f"/api/v1/analyses/{a2['id']}").json()["overall_score"]
    assert s2 > s1  # the edited version names the soft skills the job asks for


def test_pasted_resume_and_job_update(ana):
    r = ana.post("/api/v1/resumes/text", json={"name": "Pasted", "text": load("resume_developer.txt")})
    assert r.status_code == 201 and r.json()["file_type"] == "text"
    job = save_job(ana, "job_junior_developer.txt")
    r = ana.put(f"/api/v1/jobs/{job['id']}", json={"job_title": "Junior Dev (Remote)"})
    assert r.json()["job_title"] == "Junior Dev (Remote)"


def test_delete_resume_removes_file(ana):
    resume = upload_resume(ana)
    assert len(list(ana.storage.root.iterdir())) == 1
    assert ana.delete(f"/api/v1/resumes/{resume['id']}").status_code == 200
    assert list(ana.storage.root.iterdir()) == []
    assert ana.get(f"/api/v1/resumes/{resume['id']}").status_code == 404
    assert ana.get("/api/v1/resumes").json()["total"] == 0


def test_requires_login(api_client):
    client = api_client()
    assert client.get("/api/v1/resumes").status_code == 401
    assert client.post("/api/v1/jobs", json={"description": load("job_customer_support.txt")}).status_code == 401


# ------------------------------------------------- scenario D: privacy


def test_users_cannot_access_each_others_data(api_client):
    a = api_client()
    register(a, "a@example.com")
    resume = upload_resume(a)
    job = save_job(a)
    analysis = a.post("/api/v1/analyses", json={"resume_id": resume["id"], "job_id": job["id"]}).json()

    b = api_client()
    register(b, "b@example.com")
    for url in (f"/api/v1/resumes/{resume['id']}", f"/api/v1/resumes/{resume['id']}/parsed",
                f"/api/v1/resumes/{resume['id']}/versions", f"/api/v1/jobs/{job['id']}",
                f"/api/v1/analyses/{analysis['id']}"):
        assert b.get(url).status_code == 404, url
    assert b.delete(f"/api/v1/resumes/{resume['id']}").status_code == 404
    assert b.put(f"/api/v1/jobs/{job['id']}", json={"job_title": "x"}).status_code == 404
    r = b.post("/api/v1/analyses", json={"resume_id": resume["id"], "job_id": job["id"]})
    assert r.status_code == 404
    assert b.get("/api/v1/resumes").json()["total"] == 0
    assert b.get("/api/v1/analyses").json()["total"] == 0


def test_account_deletion_removes_everything(ana):
    upload_resume(ana)
    save_job(ana)
    r = ana.request("DELETE", "/api/v1/account", json={"password": "wrong-password-1"})
    assert r.status_code == 401
    r = ana.request("DELETE", "/api/v1/account", json={"password": PASSWORD})
    assert r.status_code == 200
    assert list(ana.storage.root.iterdir()) == []
    assert ana.get("/api/v1/auth/me").status_code == 401

    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.db_models import JobDescription, Resume, User

    with SessionLocal() as s:
        for model in (User, Resume, JobDescription):
            assert s.scalar(select(func.count()).select_from(model)) == 0


def test_guest_mode_needs_no_account(api_client):
    r = api_client().post("/api/v1/analyses/guest", data={"resume_text": load("resume_call_agent.txt"),
                                                          "job_text": load("job_customer_support.txt")})
    assert r.status_code == 200
