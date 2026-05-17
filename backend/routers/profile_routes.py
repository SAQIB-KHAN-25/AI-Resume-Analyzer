"""
User Profile routes - upload/replace/get a user's primary resume profile.

Each user has at most ONE active resume profile. Uploading a new resume
replaces the previous one and recomputes analytics (experience summary,
skills, predicted roles).
"""
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List

from bson import Binary
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from ..database import get_database, get_user_profiles_collection
from ..services.resume_parser import parse_resume
from ..services.role_prediction import predict_roles
from .auth_routes import get_current_user

router = APIRouter(tags=["User Profile"])
logger = logging.getLogger(__name__)

ALLOWED_RESUME_EXT = {".pdf", ".docx"}


async def _save_temp_upload(file: UploadFile) -> tuple[str, bytes]:
    """Persist UploadFile to a temp path and return (path, raw_bytes)."""
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename or "upload")
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{safe_name}")
    content = await file.read()
    with open(temp_path, "wb") as f:
        f.write(content)
    return temp_path, content


# ---------- categorization helpers ----------

PROGRAMMING_LANGUAGES = {
    "python", "java", "c", "c++", "c#", "javascript", "typescript", "go", "ruby",
    "php", "swift", "kotlin", "rust", "scala", "perl", "r", "matlab", "html", "html5",
    "css", "css3", "sass", "less", "sql",
}

FRAMEWORKS_TOOLS = {
    "react", "angular", "vue", "node", "node.js", "express", "django", "flask",
    "fastapi", "spring", "spring boot", "rails", "laravel", "tensorflow", "pytorch",
    "keras", "scikit-learn", "pandas", "numpy", "docker", "kubernetes", "git",
    "jenkins", "aws", "azure", "gcp", "firebase", "mongodb", "postgresql", "mysql",
    "redis", "graphql", "rest api", "machine learning", "deep learning",
}


def _categorize_skills(skills: List[str]) -> Dict[str, List[str]]:
    """Group skills into Programming / Frameworks & Tools / Other."""
    programming, frameworks, other = [], [], []
    seen = set()
    for raw in skills or []:
        s = str(raw).strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        if key in PROGRAMMING_LANGUAGES:
            programming.append(s)
        elif key in FRAMEWORKS_TOOLS:
            frameworks.append(s)
        else:
            other.append(s)
    return {
        "programming": programming,
        "frameworks_tools": frameworks,
        "other": other,
    }


def _experience_summary(resume_data: Dict[str, Any]) -> Dict[str, int]:
    certs = len(resume_data.get("certifications", []) or [])
    projects = len(resume_data.get("projects", []) or [])
    edu = resume_data.get("education")
    if isinstance(edu, list):
        education = len([e for e in edu if e])
    elif isinstance(edu, str) and edu.strip():
        education = 1
    elif isinstance(edu, dict):
        education = 1 if any(edu.values()) else 0
    else:
        education = 0
    return {
        "certifications": certs,
        "education": education,
        "projects": projects,
        "total": certs + education + projects,
    }


EXPECTED_SECTIONS = ("summary", "skills", "experience", "education", "projects", "certifications")
WEAK_PHRASES = ("worked on", "responsible for", "helped with", "involved in", "participated in")
ACTION_VERBS = (
    "developed", "implemented", "designed", "built", "led", "optimized", "delivered",
    "managed", "created", "deployed", "engineered", "automated", "improved", "reduced",
    "increased", "launched", "architected", "owned", "mentored", "shipped",
)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        return int(str(value).strip().split()[0])
    except (ValueError, IndexError):
        return default


def _compute_resume_ats(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a JD-less ATS-style score reflecting intrinsic resume quality.

    Components (each 0-100, then weighted):
      - section_completeness  (30%)  Summary/Skills/Experience/Education/Projects/Certifications
      - skill_breadth         (20%)  10+ skills = full
      - experience_signal     (10%)  any years present
      - education_signal      (10%)  any education entry
      - contact_completeness  (10%)  email + phone (+ linkedin/github bonus)
      - structure_quality     (20%)  action verbs, no weak phrases, has summary
    """
    raw_text = str(resume_data.get("raw_text", "") or "").lower()

    # Section completeness
    sections_present = []
    if resume_data.get("summary"):
        sections_present.append("summary")
    if resume_data.get("skills"):
        sections_present.append("skills")
    if resume_data.get("experience") or resume_data.get("work_experience"):
        sections_present.append("experience")
    edu = resume_data.get("education")
    if edu and (isinstance(edu, str) and edu.strip() or isinstance(edu, list) and any(edu) or isinstance(edu, dict) and any(edu.values())):
        sections_present.append("education")
    if resume_data.get("projects"):
        sections_present.append("projects")
    if resume_data.get("certifications"):
        sections_present.append("certifications")
    section_score = (len(sections_present) / len(EXPECTED_SECTIONS)) * 100

    # Skill breadth
    skills = resume_data.get("skills") or []
    skill_score = min(len(skills) / 10.0, 1.0) * 100

    # Experience signal
    years = _safe_int(resume_data.get("experience"))
    experience_score = 100.0 if years >= 1 else (60.0 if resume_data.get("work_experience") else 0.0)

    # Education signal
    education_score = 100.0 if "education" in sections_present else 0.0

    # Contact completeness
    info = resume_data.get("additional_info") or {}
    contact_points = 0
    if info.get("email"):
        contact_points += 50
    if info.get("phone"):
        contact_points += 35
    if info.get("linkedin"):
        contact_points += 10
    if info.get("github"):
        contact_points += 5
    contact_score = min(contact_points, 100)

    # Structure quality
    summary_text = str(resume_data.get("summary", "") or "").strip()
    has_summary = bool(summary_text)
    weak_count = sum(raw_text.count(p) for p in WEAK_PHRASES)
    action_hits = sum(1 for v in ACTION_VERBS if v in raw_text)
    structure_score = 0.0
    structure_score += 35 if has_summary else 0
    structure_score += min(action_hits / 5.0, 1.0) * 45  # up to 5 distinct action verbs
    structure_score += max(0, 20 - weak_count * 5)       # penalize weak phrases

    breakdown = {
        "section_completeness": round(section_score, 2),
        "skill_breadth": round(skill_score, 2),
        "experience_signal": round(experience_score, 2),
        "education_signal": round(education_score, 2),
        "contact_completeness": round(contact_score, 2),
        "structure_quality": round(min(structure_score, 100), 2),
    }

    weighted = (
        section_score * 0.30
        + skill_score * 0.20
        + experience_score * 0.10
        + education_score * 0.10
        + contact_score * 0.10
        + min(structure_score, 100) * 0.20
    )
    ats_score = round(weighted, 2)

    if ats_score >= 80:
        label = "Excellent"
    elif ats_score >= 65:
        label = "Good"
    elif ats_score >= 45:
        label = "Needs Improvement"
    else:
        label = "Poor"

    missing_sections = [s for s in EXPECTED_SECTIONS if s not in sections_present]

    return {
        "ats_score": ats_score,
        "label": label,
        "breakdown": breakdown,
        "sections_present": sections_present,
        "missing_sections": missing_sections,
        "skill_count": len(skills),
        "weak_phrase_count": weak_count,
        "action_verb_hits": action_hits,
    }


def _build_profile_assessment(
    resume_data: Dict[str, Any],
    predicted_roles: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a verdict + ATS bundle for the Dashboard, computed from the
    uploaded resume alone (no JD required).
    """
    ats = _compute_resume_ats(resume_data)
    ats_score = ats["ats_score"]
    top = predicted_roles[0] if predicted_roles else None
    role_score = float(top.get("score", 0) or 0) if top else 0.0

    # Readiness blends ATS heavily with role-fit signal
    readiness = ats_score * 0.7 + role_score * 0.3

    if readiness >= 75 and ats_score >= 70:
        status = "excellent"
        headline = "Your resume is ready!"
        message = (
            f"Excellent work — your resume is well-structured, ATS-friendly, and "
            f"strongly aligned with {top['role']}. You are ready to apply."
            if top else
            "Excellent work — your resume is well-structured and ATS-friendly. You are ready to apply."
        )
        next_steps = [
            "Tailor your summary to mention your target role keyword in the first line.",
            "Quantify achievements (numbers, percentages, scale) in your top 3 bullets.",
            "Apply now — your resume is in great shape.",
        ]
    elif readiness >= 60 and ats_score >= 55:
        status = "good"
        headline = "Your resume is solid — minor polish recommended"
        message = (
            f"Your resume is in good shape and a strong match for {top['role']}. "
            f"A few targeted improvements will push it from good to outstanding."
            if top else
            "Your resume is in good shape. A few targeted improvements will push it to outstanding."
        )
        next_steps = []
        if ats["missing_sections"]:
            next_steps.append(
                f"Add the following sections: {', '.join(ats['missing_sections'])}."
            )
        next_steps.extend([
            "Strengthen action verbs and quantify outcomes across experience bullets.",
            "Aim for at least 10 distinct skills covering languages, tools and frameworks.",
        ])
    elif readiness >= 40:
        status = "needs_work"
        headline = "Your resume needs work"
        message = (
            "Your resume isn't quite up to the mark yet. The fundamentals are there, "
            "but it needs more focused effort before you start applying. "
            "Don't get discouraged — keep building skills and projects."
        )
        next_steps = []
        if ats["missing_sections"]:
            next_steps.append(
                f"Add missing sections: {', '.join(ats['missing_sections'])}."
            )
        if ats["skill_count"] < 8:
            next_steps.append("List more skills — aim for 10+ across languages, tools and frameworks.")
        if ats["weak_phrase_count"]:
            next_steps.append(
                "Replace weak phrases like 'worked on' with strong verbs like 'Developed', 'Built', 'Optimized'."
            )
        next_steps.append("Aim to raise your ATS score above 70 before applying to top roles.")
        if top:
            next_steps.append(f"Aspirational target: {top['role']} — keep building toward it.")
    else:
        status = "poor"
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
            "Re-upload your resume after improving — track your progress over time.",
        ]
        if ats["missing_sections"]:
            next_steps.insert(0, f"Critical: add these missing sections — {', '.join(ats['missing_sections'])}.")

    is_ready = status in ("excellent", "good")
    recommended_role = (
        {"role": top["role"], "score": role_score} if top else None
    )
    alternative_roles = [
        {"role": r.get("role", ""), "score": float(r.get("score", 0) or 0)}
        for r in (predicted_roles or [])[1:3]
        if r.get("role")
    ]

    return {
        "ats": ats,
        "verdict": {
            "status": status,
            "headline": headline,
            "message": message,
            "is_ready": is_ready,
            "recommended_role": recommended_role,
            "alternative_roles": alternative_roles,
            "next_steps": next_steps,
            "ats_score": ats_score,
            "role_fit_score": round(role_score, 2),
        },
    }


def _serialize_profile(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Strip Mongo _id, drop binary file blob, and convert datetimes for JSON."""
    out = dict(doc)
    out.pop("_id", None)
    out.pop("file_data", None)
    out["has_file"] = bool(doc.get("file_data"))
    for key in ("created_at", "updated_at"):
        if isinstance(out.get(key), datetime):
            out[key] = out[key].isoformat()
    return out


# ---------- routes ----------

@router.post("/profile/upload")
async def upload_profile_resume(
    resume_file: UploadFile = File(..., description="Resume file (PDF or DOCX)"),
    current_user=Depends(get_current_user),
):
    """
    Parse a resume and save it as the user's primary profile.
    If a profile already exists for the user it is REPLACED.
    """
    if get_database() is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    ext = os.path.splitext(resume_file.filename or "")[1].lower()
    if ext not in ALLOWED_RESUME_EXT:
        raise HTTPException(status_code=400, detail="Only .pdf or .docx files are supported")

    temp_path, raw_bytes = await _save_temp_upload(resume_file)
    try:
        file_type = "pdf" if ext == ".pdf" else "docx"
        resume_data = parse_resume(temp_path, file_type)
        if "error" in resume_data:
            raise HTTPException(status_code=400, detail=resume_data["error"])

        skills = resume_data.get("skills", []) or []
        predicted_roles = predict_roles(skills)
        skills_grouped = _categorize_skills(skills)
        exp_summary = _experience_summary(resume_data)
        assessment = _build_profile_assessment(resume_data, predicted_roles)

        user_id = str(current_user["_id"])
        now = datetime.utcnow()

        content_type = (
            "application/pdf" if file_type == "pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        profile_doc = {
            "user_id": user_id,
            "user_name": current_user.get("full_name"),
            "user_email": current_user.get("email"),
            "file_name": resume_file.filename,
            "file_type": file_type,
            "content_type": content_type,
            "file_data": Binary(raw_bytes),
            "resume": {
                "name": resume_data.get("name"),
                "email": (resume_data.get("additional_info") or {}).get("email"),
                "phone": (resume_data.get("additional_info") or {}).get("phone"),
                "linkedin": (resume_data.get("additional_info") or {}).get("linkedin"),
                "github": (resume_data.get("additional_info") or {}).get("github"),
                "summary": resume_data.get("summary", ""),
                "skills": skills,
                "education": resume_data.get("education"),
                "experience": resume_data.get("experience"),
                "work_experience": resume_data.get("work_experience", []),
                "projects": resume_data.get("projects", []),
                "certifications": resume_data.get("certifications", []),
                "languages": resume_data.get("languages", []),
                "achievements": resume_data.get("achievements", []),
            },
            "skills_grouped": skills_grouped,
            "experience_summary": exp_summary,
            "predicted_roles": predicted_roles,
            "assessment": assessment,
            "updated_at": now,
        }

        # Upsert (replace existing profile entirely, keep created_at if present)
        existing = await get_user_profiles_collection().find_one({"user_id": user_id})
        if existing:
            profile_doc["created_at"] = existing.get("created_at", now)
            await get_user_profiles_collection().replace_one(
                {"user_id": user_id}, profile_doc
            )
        else:
            profile_doc["created_at"] = now
            await get_user_profiles_collection().insert_one(profile_doc)

        return _serialize_profile(profile_doc)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Profile upload failed")
        raise HTTPException(status_code=500, detail=f"Failed to process resume: {exc}")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


@router.get("/profile")
async def get_profile(current_user=Depends(get_current_user)):
    """Return the user's primary resume profile (or 404 if none)."""
    if get_database() is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    user_id = str(current_user["_id"])
    doc = await get_user_profiles_collection().find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="No resume profile uploaded yet")
    return _serialize_profile(doc)


@router.get("/profile/resume/file")
async def get_profile_resume_file(current_user=Depends(get_current_user)):
    """Stream the original resume file (PDF/DOCX) back to the user."""
    if get_database() is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    user_id = str(current_user["_id"])
    doc = await get_user_profiles_collection().find_one({"user_id": user_id})
    if not doc or not doc.get("file_data"):
        raise HTTPException(status_code=404, detail="No resume file stored")

    file_bytes = bytes(doc["file_data"])
    content_type = doc.get("content_type") or "application/octet-stream"
    file_name = doc.get("file_name") or f"resume.{doc.get('file_type', 'pdf')}"

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{file_name}"'},
    )


@router.delete("/profile")
async def delete_profile(current_user=Depends(get_current_user)):
    """Delete the user's stored resume profile."""
    if get_database() is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    user_id = str(current_user["_id"])
    result = await get_user_profiles_collection().delete_one({"user_id": user_id})
    return {"deleted": result.deleted_count}
