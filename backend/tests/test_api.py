import pytest

pytest.importorskip("fastapi")
pytest.importorskip("multipart")

from .conftest import load  # noqa: E402


@pytest.fixture
def client(api_client):
    return api_client()


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analysis_with_pasted_resume(client):
    r = client.post("/api/v1/analyses/guest", data={"resume_text": load("resume_call_agent.txt"),
                                               "job_text": load("job_customer_support.txt")})
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["overall_score"] <= 100
    assert body["keyword_matches"]
    assert len(body["components"]) == 6


def test_analysis_with_uploaded_file(client):
    files = {"resume_file": ("resume.txt", load("resume_developer.txt").encode(), "text/plain")}
    r = client.post("/api/v1/analyses/guest", data={"job_text": load("job_junior_developer.txt")}, files=files)
    assert r.status_code == 200
    assert r.json()["job_category"] == "software_development"


def test_missing_job_description_is_rejected(client):
    r = client.post("/api/v1/analyses/guest", data={"resume_text": load("resume_call_agent.txt")})
    assert r.status_code == 422


def test_missing_resume_is_rejected(client):
    r = client.post("/api/v1/analyses/guest", data={"job_text": load("job_customer_support.txt")})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "MISSING_RESUME"


def test_unsupported_upload_is_rejected(client):
    files = {"resume_file": ("resume.exe", b"MZ\x90\x00binary", "application/octet-stream")}
    r = client.post("/api/v1/analyses/guest", data={"job_text": load("job_customer_support.txt")}, files=files)
    assert r.status_code == 415
    assert r.json()["code"] == "UNSUPPORTED_TYPE"


def test_parse_job_endpoint(client):
    r = client.post("/api/v1/jobs/parse", json={"text": load("job_junior_developer.txt")})
    assert r.status_code == 200
    names = {k["name"] for k in r.json()["keywords"]}
    assert {"Java", "React", "PostgreSQL"} <= names


def test_state_changing_requests_need_csrf_header(client):
    client.headers.pop("X-Requested-With")
    r = client.post("/api/v1/jobs/parse", json={"text": load("job_junior_developer.txt")})
    assert r.status_code == 403
    assert r.json()["code"] == "CSRF_HEADER_MISSING"
