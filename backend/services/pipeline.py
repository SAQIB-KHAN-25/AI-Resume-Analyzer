"""
Unified analysis pipeline orchestrator.

Runs the full flow:
  Resume parse -> JD parse -> Skill extraction (already done by parsers)
  -> Match -> ATS -> Role prediction -> Recommendations
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .matching_engine import calculate_match_score
from .ats_scoring import calculate_ats_score
from .role_prediction import predict_roles
from .recommendation_engine import generate_recommendations
from .verdict_engine import build_verdict

logger = logging.getLogger(__name__)


# Sections we expect a strong resume to contain (used by ATS)
SECTION_KEYWORDS = {
    "education": ["education", "academic"],
    "experience": ["experience", "employment", "work history"],
    "skills": ["skills", "technical skills", "core competencies"],
    "projects": ["projects", "personal projects"],
    "certifications": ["certifications", "certificates"],
    "summary": ["summary", "objective", "profile"],
}


def detect_sections(resume_text: str) -> List[str]:
    """Detect which standard resume sections exist in the raw text."""
    if not resume_text:
        return []
    lowered = resume_text.lower()
    found = []
    for section, aliases in SECTION_KEYWORDS.items():
        if any(alias in lowered for alias in aliases):
            found.append(section)
    return found


def _flatten_ats_recommendations(recs: Any) -> List[str]:
    """
    The ATS engine returns a structured dict with 'overall_assessment',
    'strengths', 'critical_improvements', 'important_improvements',
    'suggestions', 'improvement_potential'. The API contract expects a
    flat List[str], so we flatten while preserving priority order.
    """
    if recs is None:
        return []
    if isinstance(recs, list):
        return [str(r).strip() for r in recs if str(r).strip()]
    if not isinstance(recs, dict):
        return [str(recs).strip()] if str(recs).strip() else []

    flat: List[str] = []
    overall = recs.get("overall_assessment")
    if isinstance(overall, str) and overall.strip():
        flat.append(overall.strip())

    for key in ("critical_improvements", "important_improvements", "suggestions", "strengths"):
        items = recs.get(key) or []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    text = item.get("recommendation") or item.get("message") or item.get("text")
                    if text:
                        flat.append(str(text).strip())
                elif isinstance(item, str) and item.strip():
                    flat.append(item.strip())
        elif isinstance(items, str) and items.strip():
            flat.append(items.strip())

    # Deduplicate while preserving order
    seen = set()
    unique: List[str] = []
    for line in flat:
        norm = line.lower()
        if norm and norm not in seen:
            seen.add(norm)
            unique.append(line)
    return unique


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        return int(str(value).strip().split()[0])
    except (ValueError, IndexError):
        return default


def run_full_analysis(
    resume_data: Dict[str, Any],
    jd_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run the complete analysis pipeline end-to-end.

    Args:
        resume_data: Parsed resume from `parse_resume()`
        jd_data: Parsed JD from `process_job_description()`

    Returns:
        Dict with keys: match, ats, predicted_roles, recommendations
    """
    resume_skills: List[str] = resume_data.get("skills", []) or []
    jd_skills: List[str] = jd_data.get("required_skills", []) or []
    jd_keywords: List[str] = jd_data.get("keywords", []) or []
    resume_text: str = resume_data.get("raw_text", "") or ""

    # 1. Match
    match_result = calculate_match_score(resume_skills, jd_skills)

    # 2. ATS
    sections = detect_sections(resume_text)
    experience_years = _safe_int(resume_data.get("experience"))
    required_experience = _safe_int(jd_data.get("experience_required"))

    ats_result = calculate_ats_score({
        "resume_keywords": resume_skills + jd_keywords[:0],  # use skills as keyword proxy
        "jd_keywords": jd_keywords,
        "resume_skills": resume_skills,
        "jd_skills": jd_skills,
        "sections": sections,
        "resume_education": [resume_data.get("education", "")] if resume_data.get("education") else [],
        "required_education": [jd_data.get("education_required", "")] if jd_data.get("education_required") else [],
        "experience_years": experience_years,
        "required_experience": required_experience,
        "resume_text": resume_text,
    })

    # 3. Predicted roles
    predicted_roles = predict_roles(resume_skills)

    # 4. Recommendations
    recommendations = generate_recommendations(
        missing_skills=match_result.get("missing_skills", []),
        ats_score=ats_result.get("ats_score", 0),
        predicted_roles=predicted_roles,
        resume_data=resume_data,
    )

    # 5. Verdict
    verdict = build_verdict(
        ats_score=ats_result.get("ats_score", 0),
        match_score=match_result.get("match_score", 0),
        predicted_roles=predicted_roles,
        missing_skills=match_result.get("missing_skills", []),
    )

    return {
        "match": {
            "match_score": match_result["match_score"],
            "matched_skills": match_result["matched_skills"],
            "missing_skills": match_result["missing_skills"],
            "total_jd_skills": match_result["total_jd_skills"],
            "matched_count": match_result["matched_count"],
        },
        "ats": {
            "ats_score": ats_result["ats_score"],
            "score_category": ats_result["score_category"],
            "score_label": ats_result["score_label"],
            "breakdown": ats_result["breakdown"],
            "recommendations": _flatten_ats_recommendations(ats_result.get("recommendations")),
        },
        "predicted_roles": predicted_roles,
        "recommendations": recommendations,
        "verdict": verdict,
    }
