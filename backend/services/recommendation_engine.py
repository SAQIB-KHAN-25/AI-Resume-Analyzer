from __future__ import annotations

from typing import Any, Dict, List


ROLE_SKILL_GUIDANCE = {
    "backend": "Focus on REST APIs, database design, distributed systems, and backend frameworks like FastAPI/Django.",
    "frontend": "Improve UI architecture, accessibility, component design, and modern React/TypeScript patterns.",
    "full stack": "Build end-to-end projects with frontend + backend integration, authentication, and production deployment.",
    "data": "Strengthen SQL, data modeling, analytics workflows, and data pipeline tooling.",
    "devops": "Improve CI/CD, Docker/Kubernetes, observability, and cloud infrastructure skills.",
    "ml": "Build applied ML projects with model evaluation, deployment, and MLOps best practices.",
    "qa": "Demonstrate test automation depth with API/UI/performance test coverage and quality metrics.",
}

WEAK_PHRASES = [
    "worked on",
    "responsible for",
    "helped with",
    "involved in",
    "participated in",
]


def _role_based_recommendation(predicted_roles: List[Dict[str, Any]]) -> str | None:
    if not predicted_roles:
        return None

    top_role = str(predicted_roles[0].get("role", "")).strip()
    if not top_role:
        return None

    role_lower = top_role.lower()
    for key, guidance in ROLE_SKILL_GUIDANCE.items():
        if key in role_lower:
            return f"For your top predicted role ({top_role}), {guidance}"

    return f"Focus your resume and project portfolio on skills required for {top_role}."


def _resume_writing_recommendations(resume_data: Dict[str, Any] | None) -> List[str]:
    if not resume_data:
        return []

    recs: List[str] = []
    summary = str(resume_data.get("summary", "") or "").strip()
    raw_text = str(resume_data.get("raw_text", "") or "")

    if not summary:
        recs.append("Add a concise 2-3 line summary highlighting your domain, years of experience, and strongest technical skills.")

    raw_lower = raw_text.lower()
    weak_hits = [phrase for phrase in WEAK_PHRASES if phrase in raw_lower]
    if weak_hits:
        recs.append("Replace weak phrases (for example: 'worked on') with strong action verbs like 'Developed', 'Implemented', and 'Optimized'.")

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    bullet_line_count = sum(1 for line in lines if line.startswith(("-", "*", "•")))
    if lines and bullet_line_count < 3:
        recs.append("Improve formatting with bullet points for achievements and measurable outcomes in each project/experience section.")

    return recs


def generate_recommendations(
    missing_skills: List[str],
    ats_score: float,
    predicted_roles: List[Dict[str, Any]],
    resume_data: Dict[str, Any] | None = None,
) -> List[str]:
    """Generate personalized recommendations for profile improvement."""
    recommendations: List[str] = []

    # Missing skill recommendations
    cleaned_missing = [str(skill).strip() for skill in missing_skills if str(skill).strip()]
    if cleaned_missing:
        top_missing = cleaned_missing[:6]
        recommendations.append(
            f"Add projects or certifications covering missing skills: {', '.join(top_missing)}."
        )
        if any(skill.lower() in {"docker", "kubernetes"} for skill in top_missing):
            recommendations.append("Add hands-on deployment projects using Docker and Kubernetes to strengthen your backend profile.")

    # ATS-based recommendations
    if ats_score < 50:
        recommendations.append("ATS score is low: improve resume structure with clear sections (Summary, Skills, Experience, Projects, Education).")
        recommendations.append("Increase keyword relevance by aligning resume skills/phrases with job requirements.")
    elif ats_score < 70:
        recommendations.append("ATS score is moderate: add more role-specific skills and impactful keywords in experience bullet points.")
    else:
        recommendations.append("ATS score is strong: focus on minor improvements such as quantifying achievements and tightening wording.")

    # Role-based recommendation
    role_recommendation = _role_based_recommendation(predicted_roles)
    if role_recommendation:
        recommendations.append(role_recommendation)

    # Resume writing recommendations
    recommendations.extend(_resume_writing_recommendations(resume_data))

    # Remove duplicates while preserving order
    unique_recommendations: List[str] = []
    seen = set()
    for rec in recommendations:
        normalized = rec.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique_recommendations.append(rec)

    return unique_recommendations
