"""
Verdict engine — synthesizes ATS + match + role-fit scores into a single
human-friendly verdict telling the candidate whether their resume is ready
and which role they are best suited for, or whether they need to work harder.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


VERDICT_STATUS = ("excellent", "good", "needs_work", "poor")


def _pick_top_role(predicted_roles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not predicted_roles:
        return None
    top = max(predicted_roles, key=lambda r: float(r.get("score", 0) or 0))
    return top if float(top.get("score", 0) or 0) > 0 else None


def _classify(ats_score: float, match_score: float, role_score: float) -> str:
    """
    Compute a single verdict status from three independent signals.

    Uses a weighted readiness score so a strong resume isn't penalized for a
    poorly-aligned JD, but a weak resume can't hide behind a great JD match.
    """
    readiness = (ats_score * 0.5) + (role_score * 0.3) + (match_score * 0.2)

    if readiness >= 75 and ats_score >= 70:
        return "excellent"
    if readiness >= 60 and ats_score >= 55:
        return "good"
    if readiness >= 40:
        return "needs_work"
    return "poor"


def build_verdict(
    ats_score: float,
    match_score: float,
    predicted_roles: List[Dict[str, Any]],
    missing_skills: List[str],
) -> Dict[str, Any]:
    """
    Build a structured verdict object the frontend can render directly.

    Returns:
        {
            "status": "excellent" | "good" | "needs_work" | "poor",
            "headline": str,
            "message": str,
            "recommended_role": {"role": str, "score": float} | None,
            "alternative_roles": [{"role": str, "score": float}, ...],
            "next_steps": [str, ...],
            "is_ready": bool,
        }
    """
    ats = float(ats_score or 0)
    match = float(match_score or 0)
    top = _pick_top_role(predicted_roles or [])
    role_score = float(top.get("score", 0) or 0) if top else 0.0

    status = _classify(ats, match, role_score)
    is_ready = status in ("excellent", "good")

    alternative_roles = [
        {"role": r.get("role", ""), "score": float(r.get("score", 0) or 0)}
        for r in (predicted_roles or [])[1:3]
        if r.get("role")
    ]
    recommended_role = (
        {"role": top.get("role", ""), "score": role_score} if top else None
    )

    top_missing = [str(s).strip() for s in (missing_skills or []) if str(s).strip()][:5]

    if status == "excellent":
        headline = "Your resume is ready!"
        if recommended_role:
            message = (
                f"Excellent work — your resume is well-structured, ATS-friendly, and "
                f"strongly aligned with the role of {recommended_role['role']}. "
                f"You are a great fit and ready to apply."
            )
        else:
            message = (
                "Excellent work — your resume is well-structured and ATS-friendly. "
                "You are ready to apply."
            )
        next_steps = [
            "Tailor your summary to mention the target role keyword in the first line.",
            "Quantify achievements (numbers, percentages, scale) in your top 3 bullets.",
            "Apply now — your resume is in great shape.",
        ]

    elif status == "good":
        headline = "Your resume is solid — minor polish recommended"
        if recommended_role:
            message = (
                f"Your resume is in good shape and a strong match for "
                f"{recommended_role['role']}. A few targeted improvements will push it "
                f"from good to outstanding."
            )
        else:
            message = (
                "Your resume is in good shape. A few targeted improvements will push "
                "it from good to outstanding."
            )
        next_steps = []
        if top_missing:
            next_steps.append(
                f"Add 1-2 projects covering: {', '.join(top_missing[:3])}."
            )
        next_steps.extend([
            "Strengthen action verbs and quantify outcomes across your experience.",
            "Ensure every section (Summary, Skills, Experience, Projects) is present.",
        ])

    elif status == "needs_work":
        headline = "Your resume needs work"
        message = (
            "Your resume isn't quite up to the mark yet. The fundamentals are there, "
            "but it needs more focused effort before you start applying. "
            "Don't get discouraged — keep building your skills and projects, and your "
            "resume will get there."
        )
        next_steps = []
        if top_missing:
            next_steps.append(
                f"Build hands-on projects with: {', '.join(top_missing[:4])}."
            )
        next_steps.extend([
            "Improve resume structure — add Summary, clear Skills, and Projects sections.",
            "Add measurable outcomes (numbers, impact) to every experience bullet.",
            "Aim to raise your ATS score above 70% before applying to top roles.",
        ])
        if recommended_role:
            next_steps.append(
                f"Aspirational target: {recommended_role['role']} — keep building toward it."
            )

    else:  # poor
        headline = "Your resume is not up to the mark"
        message = (
            "Your resume needs significant improvement. This is not a reason to give up — "
            "it's a clear signal to work harder. Focus on building real projects, "
            "learning in-demand skills, and structuring your resume professionally. "
            "Every great career starts with consistent effort. Keep going."
        )
        next_steps = [
            "Pick 2-3 in-demand skills from your target role and learn them deeply.",
            "Build at least 2 substantial projects that demonstrate those skills.",
            "Rewrite your resume with clear sections: Summary, Skills, Projects, Education.",
            "Use action verbs and quantify every achievement.",
            "Re-run this analysis once you have improved — track your progress over time.",
        ]
        if top_missing:
            next_steps.insert(
                0,
                f"Critical skill gaps to address first: {', '.join(top_missing[:4])}.",
            )

    return {
        "status": status,
        "headline": headline,
        "message": message,
        "recommended_role": recommended_role,
        "alternative_roles": alternative_roles,
        "next_steps": next_steps,
        "is_ready": is_ready,
        "ats_score": round(ats, 2),
        "match_score": round(match, 2),
        "role_fit_score": round(role_score, 2),
    }

