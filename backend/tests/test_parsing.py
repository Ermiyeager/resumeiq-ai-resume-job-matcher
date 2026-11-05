from app.engine.job_parser import parse_job
from app.engine.keywords import find_skills
from app.engine.models import Importance, RequirementType
from app.engine.resume_parser import experience_months, parse_resume

from .conftest import TODAY, load


def names(hits):
    return {h.skill.name for h in hits}


def test_multiword_and_longest_match_wins():
    hits = find_skills("Handled inbound customer calls and booked meetings with prospects.")
    assert {"Inbound calls", "Appointment setting"} <= names(hits)
    # "calls" inside "inbound customer calls" must not also produce a separate hit
    assert sum(h.skill.name == "Phone support" for h in hits) == 0


def test_abbreviations_and_variations_normalize():
    assert "REST APIs" in names(find_skills("Built RESTful services"))
    assert "PostgreSQL" in names(find_skills("Experience with Postgres"))
    assert "Node.js" in names(find_skills("APIs in NodeJS"))
    assert "C++" in names(find_skills("Wrote C++ code"))


def test_word_boundaries_avoid_false_positives():
    assert "Excel" not in names(find_skills("Excellent communicator"))
    assert "Java" not in names(find_skills("JavaScript developer"))


def test_resume_sections_detected():
    resume = parse_resume(load("resume_developer.txt"), today=TODAY)
    for section in ("summary", "skills", "experience", "projects", "education", "interests"):
        assert section in resume.sections


def test_inferred_skills_are_not_explicit():
    resume = parse_resume(load("resume_developer.txt"), today=TODAY)
    java = next(s for s in resume.skills if s.name == "Java")
    assert java.explicit  # listed in Skills
    git = next(s for s in resume.skills if s.name == "Git")
    assert not git.explicit  # only inferred from GitHub


def test_skill_in_weak_context_is_flagged():
    resume = parse_resume(load("resume_developer.txt"), today=TODAY)
    docker = next(s for s in resume.skills if s.name == "Docker")
    assert docker.only_weak


def test_duplicate_skills_are_merged():
    resume = parse_resume("Skills\nPython, python, PYTHON\nExperience\nWrote Python scripts daily for reports.",
                          today=TODAY)
    assert [s.name for s in resume.skills].count("Python") == 1


def test_experience_dates_merge_overlaps():
    months, ranges = experience_months("Jan 2020 - Dec 2020\nJun 2020 - Jun 2021", TODAY)
    assert months == 18
    assert len(ranges) == 2


def test_experience_present_uses_today():
    months, _ = experience_months("Mar 2025 - Present", TODAY)
    assert months == 21  # Mar 2025 .. Nov 2026 inclusive


def test_education_in_progress_is_not_completed():
    resume = parse_resume("Education\nBachelor of Science in Computer Science (expected 2027)", today=TODAY)
    assert resume.education[0].in_progress
    assert resume.education[0].field == "computer science"


def test_job_requirement_classification():
    job = parse_job(load("job_junior_developer.txt"))
    kw = {k.name: k for k in job.keywords}
    assert kw["React"].requirement_type == RequirementType.MANDATORY
    assert kw["Docker"].requirement_type == RequirementType.PREFERRED
    assert kw["Unit testing"].requirement_type == RequirementType.RESPONSIBILITY
    assert job.degree is not None and job.degree.level == 2 and job.degree.mandatory


def test_not_required_is_preferred():
    job = parse_job("Support Agent\nRequirements\n- Customer service experience is helpful, but it is not required.\n"
                    "- Reliable internet connection")
    cs = next(k for k in job.keywords if k.name == "Customer service")
    assert cs.requirement_type == RequirementType.PREFERRED
    assert cs.importance != Importance.CRITICAL


def test_required_years_extracted():
    job = parse_job("Resolutions Specialist\nWhat we're looking for:\n- 2+ years in customer support, "
                    "resolutions, or disputes experience\n- Calm under pressure")
    assert job.required_years == 2
    assert job.required_years_mandatory


def test_job_category_detected():
    assert parse_job(load("job_customer_support.txt")).category == "customer_service"
    assert parse_job(load("job_junior_developer.txt")).category == "software_development"
