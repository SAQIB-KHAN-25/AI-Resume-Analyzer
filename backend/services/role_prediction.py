"""Role prediction utilities for Week 6 role matching."""

import json
import os
from typing import Any, Dict, List


ROLE_PROFILES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "role_profiles.json")


def load_role_profiles() -> Dict[str, List[str]]:
    """Load role profiles from JSON and normalize schema to role -> [skills]."""
    try:
        if not os.path.exists(ROLE_PROFILES_PATH):
            return {}

        with open(ROLE_PROFILES_PATH, "r", encoding="utf-8") as file:
            raw_profiles = json.load(file)

        normalized: Dict[str, List[str]] = {}
        for role, profile in raw_profiles.items():
            if isinstance(profile, list):
                normalized[role] = [str(skill) for skill in profile if str(skill).strip()]
            elif isinstance(profile, dict):
                required = profile.get("required_skills", []) or []
                optional = profile.get("optional_skills", []) or []
                combined = [str(skill) for skill in [*required, *optional] if str(skill).strip()]
                normalized[role] = combined

        return normalized
    except Exception as error:
        print(f"Warning: Could not load role profiles: {error}")
        return {}


def predict_roles(resume_skills: List[str]) -> List[Dict[str, Any]]:
    """
    Predict top roles using: (matched role skills / total role skills) * 100.
    """
    role_profiles = load_role_profiles()
    resume_set = {skill.lower().strip() for skill in resume_skills if skill and str(skill).strip()}

    results: List[Dict[str, Any]] = []
    for role, skills in role_profiles.items():
        role_set = {skill.lower().strip() for skill in skills if skill and str(skill).strip()}
        matched = sorted(list(resume_set.intersection(role_set)))
        missing = sorted(list(role_set - resume_set))
        score = (len(matched) / len(role_set)) * 100 if role_set else 0

        results.append(
            {
                "role": role,
                "score": round(score, 2),
                "matched_skills": matched,
                "missing_skills": missing,
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:5]


def predict_roles_from_skills(skills: List[str], experience: str = "") -> List[Dict[str, Any]]:
    """Backward-compatible wrapper for existing callers."""
    _ = experience
    predictions = predict_roles(skills)
    return [
        {
            "role": item["role"],
            "confidence": item["score"],
            "matched_required": item["matched_skills"],
            "matched_optional": [],
            "missing_required": item["missing_skills"],
        }
        for item in predictions
    ]


def get_role_requirements(role_name: str) -> Dict[str, Any]:
    """Get normalized skill list for a role."""
    role_profiles = load_role_profiles()
    return {"skills": role_profiles.get(role_name, [])}


def get_missing_skills(resume_skills: List[str], jd_skills: List[str]) -> List[str]:
    """Return JD skills that are missing from resume skills."""
    resume_set = {skill.lower().strip() for skill in resume_skills if skill and str(skill).strip()}
    return [skill for skill in jd_skills if skill.lower().strip() not in resume_set]


def generate_recommendations(
    missing_skills: List[str], ats_score: float, match_score: float, predicted_role: str
) -> List[str]:
    """Generate simple recommendation strings based on gaps and scores."""
    recommendations: List[str] = []

    if missing_skills:
        recommendations.append("Missing skills: " + ", ".join(missing_skills))

    if ats_score < 70:
        recommendations.append("Improve resume structure and add more keywords")

    if match_score < 60:
        recommendations.append("Add more relevant projects")

    if predicted_role == "Backend Developer":
        recommendations.append("Build backend projects using Flask/Django")

    return recommendations
