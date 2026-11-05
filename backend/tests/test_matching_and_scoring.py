import pytest

from app.config import DEFAULT_WEIGHTS, weights_for
from app.engine.analyzer import analyze
from app.engine.models import MatchType
from app.engine.scoring import combine, interpret
from app.engine.similarity import TokenOverlapBackend

from .conftest import TODAY, load


def run(resume, job, backend, **kw):
    return analyze(resume, job, today=TODAY, backend=backend, **kw)


def by_kw(report):
    return {m.keyword: m for m in report.keyword_matches}


@pytest.fixture
def dev_report(backend):
    return run(load("resume_developer.txt"), load("job_junior_developer.txt"), backend)


def test_exact_match(dev_report):
    assert by_kw(dev_report)["Java"].match_type == MatchType.EXACT_MATCH


def test_synonym_match(dev_report):
    m = by_kw(dev_report)["REST APIs"]
    assert m.match_type == MatchType.SYNONYM_MATCH
    assert "RESTful services" in m.resume_evidence


def test_inferred_skill_is_partial_not_confirmed(dev_report):
    assert by_kw(dev_report)["Git"].match_type == MatchType.PARTIAL_MATCH


def test_missing_skill(dev_report):
    assert by_kw(dev_report)["React"].match_type == MatchType.MISSING


def test_weak_context_needs_verification(dev_report):
    assert by_kw(dev_report)["Docker"].match_type == MatchType.NEEDS_VERIFICATION


def test_every_match_has_evidence(dev_report):
    for m in dev_report.keyword_matches:
        assert m.job_evidence
        if m.match_type != MatchType.MISSING:
            assert m.resume_evidence


def test_related_skill_is_not_a_match(backend):
    report = run("Skills\nMySQL, SQL\nExperience\nMaintained MySQL databases for a retail client since 2020.",
                 "Database Developer\nRequirements:\n- PostgreSQL experience required", backend)
    assert by_kw(report)["PostgreSQL"].match_type == MatchType.RELATED_SKILL


def test_technical_skills_never_semantic(backend):
    """'Experience with React' must not semantically match 'Experience with Flutter'."""
    report = run("Experience\nExperience with Flutter building mobile apps for clients.",
                 "Frontend Developer\nRequirements:\n- Experience with React", backend)
    assert by_kw(report)["React"].match_type in {MatchType.MISSING, MatchType.RELATED_SKILL}


def test_semantic_match_for_non_technical_skill():
    report = run("Experience\nResolved technical problems for customers over the phone every day.",
                 "IT Support\nRequirements:\n- Experience in technical troubleshooting", TokenOverlapBackend())
    m = by_kw(report)["Troubleshooting"]
    assert m.match_type in {MatchType.PARTIAL_MATCH, MatchType.SEMANTIC_MATCH}
    assert m.match_type not in {MatchType.EXACT_MATCH, MatchType.SYNONYM_MATCH}


def test_mandatory_requirement_absent_is_flagged(dev_report):
    react = next(i for i in dev_report.mandatory_requirements if i.requirement == "React")
    assert react.status == "NOT_FOUND"
    assert dev_report.mandatory_gaps >= 1
    assert any("React" in r.title and r.priority.value == "CRITICAL" for r in dev_report.recommendations)


def test_missing_certification_flagged_even_with_high_score(backend):
    resume = load("resume_call_agent.txt")
    job = load("job_customer_support.txt") + "\nRequirements:\n- CompTIA A+ certification required"
    report = run(resume, job, backend)
    cert = next(i for i in report.mandatory_requirements if i.requirement == "CompTIA A+")
    assert cert.kind == "certification" and cert.status == "NOT_FOUND"


def test_spec_weighted_score_example():
    scores = {"skills": 80, "experience": 70, "education": 100, "responsibilities": 75,
              "qualifications": 50, "soft_skills": 90}
    overall, _ = combine(scores, weights_for("general"))
    # 0.35*80 + 0.25*70 + 0.10*100 + 0.15*75 + 0.10*50 + 0.05*90 = 76.25
    # (the original spec printed 76.75, which is an arithmetic slip)
    assert overall == pytest.approx(76.25)


def test_unknown_components_are_excluded_not_zeroed():
    weights = weights_for("general")
    overall, eff = combine({"skills": 80, "experience": None, "education": None, "responsibilities": None,
                            "qualifications": None, "soft_skills": None}, weights)
    assert overall == pytest.approx(80)
    assert eff["experience"] == 0


def test_missing_resume_data_marked_unknown(backend):
    report = run("Skills\nCustomer service, inbound calls, scheduling and data entry for small teams.",
                 "Office Assistant\nRequirements:\n- Bachelor's degree required\n- 3+ years of experience",
                 backend)
    comps = {c.key: c for c in report.components}
    assert comps["education"].status == "UNKNOWN"
    statuses = {i.kind: i.status for i in report.mandatory_requirements}
    assert statuses["degree"] == "UNKNOWN"
    assert statuses["experience"] == "UNKNOWN"
    assert report.confidence != "High"


def test_weights_are_configurable():
    w = weights_for("general", {"skills": 0.7})
    assert sum(w.values()) == pytest.approx(1)
    assert w["skills"] > DEFAULT_WEIGHTS["skills"]
    with pytest.raises(ValueError):
        weights_for("general", {"salary": 1})


def test_score_interpretation_bands():
    assert interpret(95) == "Excellent alignment"
    assert interpret(76.25) == "Good alignment"
    assert interpret(10) == "Limited alignment"


def test_core_analysis_works_without_external_ai():
    report = run(load("resume_call_agent.txt"), load("job_customer_support.txt"), TokenOverlapBackend())
    assert 0 <= report.overall_score <= 100
    assert report.keyword_matches


def test_strong_candidate_scores_higher_than_weak(backend):
    job = load("job_customer_support.txt")
    strong = run(load("resume_call_agent.txt"), job, backend)
    weak = run(load("resume_developer.txt"), job, backend)
    assert strong.overall_score > weak.overall_score + 15
