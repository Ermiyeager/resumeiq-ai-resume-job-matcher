"""Scoring weights, configurable per job category.

Weights in each profile must sum to 1.0. Components that cannot be scored
(for example, no certifications are required) are left out and the remaining
weights are scaled up proportionally, so the result is still out of 100.
"""

from __future__ import annotations

DEFAULT_WEIGHTS: dict[str, float] = {
    "skills": 0.35,
    "experience": 0.25,
    "education": 0.10,
    "responsibilities": 0.15,
    "qualifications": 0.10,
    "soft_skills": 0.05,
}

CATEGORY_WEIGHTS: dict[str, dict[str, float]] = {
    # Contact-centre and sales roles are judged more on duties and communication than on degrees.
    "customer_service": {"skills": 0.30, "experience": 0.25, "education": 0.05,
                         "responsibilities": 0.20, "qualifications": 0.05, "soft_skills": 0.15},
    "sales": {"skills": 0.30, "experience": 0.25, "education": 0.05,
              "responsibilities": 0.20, "qualifications": 0.05, "soft_skills": 0.15},
    "administration": {"skills": 0.30, "experience": 0.25, "education": 0.05,
                       "responsibilities": 0.20, "qualifications": 0.05, "soft_skills": 0.15},
    "software_development": {"skills": 0.40, "experience": 0.20, "education": 0.10,
                             "responsibilities": 0.15, "qualifications": 0.10, "soft_skills": 0.05},
    "healthcare_administration": {"skills": 0.30, "experience": 0.20, "education": 0.10,
                                  "responsibilities": 0.15, "qualifications": 0.20, "soft_skills": 0.05},
}

COMPONENT_LABELS = {
    "skills": "Technical and functional skills",
    "experience": "Work experience",
    "education": "Education",
    "responsibilities": "Job responsibilities",
    "qualifications": "Certifications and qualifications",
    "soft_skills": "Soft skills",
}


def weights_for(category: str, override: dict[str, float] | None = None) -> dict[str, float]:
    weights = dict(CATEGORY_WEIGHTS.get(category, DEFAULT_WEIGHTS))
    if override:
        unknown = set(override) - set(DEFAULT_WEIGHTS)
        if unknown:
            raise ValueError(f"Unknown weight keys: {sorted(unknown)}")
        weights.update(override)
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Weights must add up to more than zero.")
    return {k: v / total for k, v in weights.items()}


for _name, _profile in {"default": DEFAULT_WEIGHTS, **CATEGORY_WEIGHTS}.items():
    assert abs(sum(_profile.values()) - 1.0) < 1e-9, f"weights for {_name} must sum to 1"
