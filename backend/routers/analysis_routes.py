"""
Unified analysis endpoint.

Accepts a resume file + JD text in a single multipart request, runs the full
pipeline, persists everything to MongoDB, and returns a complete analysis.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..database import (
    get_database,
    get_analysis_results_collection,
    get_resumes_collection,
    get_job_descriptions_collection,
)
from ..models.analysis_model import AnalysisResponse
from ..services.resume_parser import parse_resume, extract_text_from_pdf, extract_text_from_docx
from ..services.jd_processor import process_job_description
from ..services.pipeline import run_full_analysis
from ..services.report_generator import generate_pdf_report
from .auth_routes import get_current_user

router = APIRouter(tags=["Analysis Pipeline"])
logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(5 * 1024 * 1024)))
ALLOWED_RESUME_EXT = {".pdf", ".docx"}
ALLOWED_JD_EXT = {".pdf", ".docx", ".txt"}


async def _save_temp_upload(file: UploadFile) -> str:
    """Persist an UploadFile to a unique temp path and return the path."""
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename or "upload")
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}_{safe_name}")

    data = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    if len(data) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Max size is 5 MB.")
    with open(temp_path, "wb") as fh:
        fh.write(data)
    return temp_path


async def _extract_jd_text_from_file(jd_file: UploadFile) -> str:
    """Persist JD upload to temp, extract text via PDF/DOCX/TXT, then clean up."""
    ext = os.path.splitext(jd_file.filename or "")[1].lower()
    if ext not in ALLOWED_JD_EXT:
        raise HTTPException(
            status_code=400,
            detail="Invalid JD file type. Allowed: PDF, DOCX, TXT.",
        )

    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    safe_name = os.path.basename(jd_file.filename or "jd_upload")
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}_{safe_name}")

    data = await jd_file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    if len(data) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="JD file too large. Max size is 5 MB.")
    with open(temp_path, "wb") as fh:
        fh.write(data)

    try:
        if ext == ".pdf":
            text = extract_text_from_pdf(temp_path)
        elif ext == ".docx":
            text = extract_text_from_docx(temp_path)
        else:  # .txt
            with open(temp_path, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        return (text or "").strip()
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume_against_jd(
    resume_file: UploadFile = File(..., description="Resume file (PDF or DOCX)"),
    jd_text: Optional[str] = Form(None, description="Job description text (optional if jd_file is provided)"),
    jd_file: Optional[UploadFile] = File(None, description="Optional JD file (PDF/DOCX/TXT)"),
    job_title: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
):
    """
    Run the complete analysis pipeline in one request.

    Pipeline:
        Resume parse → JD parse → Skill match → ATS score
        → Role prediction → Recommendations → Persist to MongoDB
    """
    # Resolve JD text from either pasted text or uploaded file
    if jd_file is not None and getattr(jd_file, "filename", ""):
        try:
            jd_text = await _extract_jd_text_from_file(jd_file)
        finally:
            await jd_file.close()
        if not jd_text:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the uploaded JD file.",
            )

    if not jd_text or not jd_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description is required (paste text or upload a JD file).",
        )

    ext = os.path.splitext(resume_file.filename or "")[1].lower()
    if ext not in ALLOWED_RESUME_EXT:
        raise HTTPException(
            status_code=400,
            detail="Invalid resume type. Only PDF and DOCX are allowed.",
        )

    temp_path = await _save_temp_upload(resume_file)
    try:
        # 1. Parse resume
        file_type = "pdf" if ext == ".pdf" else "docx"
        resume_data = parse_resume(temp_path, file_type)
        if "error" in resume_data:
            raise HTTPException(status_code=400, detail=resume_data["error"])

        # 2. Parse JD
        jd_data = process_job_description(jd_text)

        # 3. Run pipeline
        pipeline_result = run_full_analysis(resume_data, jd_data)

        # 4. Persist to Mongo
        resume_id = jd_id = analysis_id = None
        if get_database() is not None:
            user_id = str(current_user["_id"])
            now = datetime.utcnow()

            resume_doc = {
                "user_id": user_id,
                "file_name": resume_file.filename,
                "file_type": file_type,
                "uploaded_at": now,
                "resume_data": resume_data,
            }
            resume_id = str((await get_resumes_collection().insert_one(resume_doc)).inserted_id)

            jd_doc = {
                "user_id": user_id,
                "source_type": "text",
                "title": job_title or "Job Description",
                "description": jd_text,
                "created_at": now,
                "jd_data": jd_data,
            }
            jd_id = str((await get_job_descriptions_collection().insert_one(jd_doc)).inserted_id)

            analysis_doc = {
                "user_id": user_id,
                "resume_id": resume_id,
                "jd_id": jd_id,
                "match_score": pipeline_result["match"]["match_score"],
                "ats_score": pipeline_result["ats"]["ats_score"],
                "matched_skills": pipeline_result["match"]["matched_skills"],
                "missing_skills": pipeline_result["match"]["missing_skills"],
                "predicted_roles": pipeline_result["predicted_roles"],
                "recommendations": pipeline_result["recommendations"],
                "verdict": pipeline_result.get("verdict", {}),
                "ats_breakdown": pipeline_result["ats"]["breakdown"],
                "resume_skills": resume_data.get("skills", []),
                "jd_skills": jd_data.get("required_skills", []),
                "required_skills": jd_data.get("required_skills", []),
                "total_jd_skills": pipeline_result["match"]["total_jd_skills"],
                "matched_count": pipeline_result["match"]["matched_count"],
                "created_at": now,
            }
            analysis_id = str(
                (await get_analysis_results_collection().insert_one(analysis_doc)).inserted_id
            )

        return AnalysisResponse(
            analysis_id=analysis_id,
            resume_id=resume_id,
            jd_id=jd_id,
            resume_data=resume_data,
            jd_data=jd_data,
            match=pipeline_result["match"],
            ats=pipeline_result["ats"],
            predicted_roles=pipeline_result["predicted_roles"],
            recommendations=pipeline_result["recommendations"],
            verdict=pipeline_result.get("verdict", {}),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Analysis pipeline failed")
        raise HTTPException(status_code=500, detail="Analysis failed")
    finally:
        await resume_file.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/analyze/{analysis_id}/report")
async def download_analysis_report(
    analysis_id: str,
    current_user=Depends(get_current_user),
):
    """Generate and download a PDF report for a previously stored analysis."""
    if get_database() is None:
        raise HTTPException(status_code=503, detail="Database is not configured")

    from bson import ObjectId
    try:
        oid = ObjectId(analysis_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid analysis id")

    doc = await get_analysis_results_collection().find_one(
        {"_id": oid, "user_id": str(current_user["_id"])}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Analysis not found")

    file_path = generate_pdf_report({
        "match_score": doc.get("match_score", 0),
        "ats_score": doc.get("ats_score", 0),
        "missing_skills": doc.get("missing_skills", []),
        "predicted_roles": doc.get("predicted_roles", []),
        "recommendations": doc.get("recommendations", []),
    })
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=os.path.basename(file_path),
    )


@router.get("/analyze/history")
async def get_analysis_history(current_user=Depends(get_current_user)):
    """Return saved analyses for the current user."""
    if get_database() is None:
        return {"history": []}

    cursor = (
        get_analysis_results_collection()
        .find({"user_id": str(current_user["_id"])})
        .sort("created_at", -1)
        .limit(50)
    )
    items = await cursor.to_list(length=50)
    history = [
        {
            "analysis_id": str(item["_id"]),
            "resume_id": item.get("resume_id"),
            "jd_id": item.get("jd_id"),
            "match_score": item.get("match_score", 0),
            "ats_score": item.get("ats_score", 0),
            "matched_skills": item.get("matched_skills", []),
            "missing_skills": item.get("missing_skills", []),
            "predicted_roles": item.get("predicted_roles", []),
            "created_at": item.get("created_at", datetime.utcnow()).isoformat(),
        }
        for item in items
    ]
    return {"history": history}


@router.delete("/analyze/history/{analysis_id}")
async def delete_analysis_history_item(
    analysis_id: str,
    current_user=Depends(get_current_user),
):
    """Delete a single analysis history entry owned by the current user."""
    if get_database() is None:
        raise HTTPException(status_code=503, detail="Database is not configured")

    from bson import ObjectId
    try:
        oid = ObjectId(analysis_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid analysis id")

    result = await get_analysis_results_collection().delete_one(
        {"_id": oid, "user_id": str(current_user["_id"])}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"deleted": True, "analysis_id": analysis_id}


@router.post("/analyze/history/delete")
async def delete_analysis_history_bulk(
    payload: dict,
    current_user=Depends(get_current_user),
):
    """
    Delete multiple analysis history entries owned by the current user.
    Body: {"analysis_ids": ["...", "..."]}  or  {"all": true}
    """
    if get_database() is None:
        raise HTTPException(status_code=503, detail="Database is not configured")

    delete_all = bool(payload.get("all"))
    ids = payload.get("analysis_ids") or []

    if not delete_all and not ids:
        raise HTTPException(status_code=400, detail="No analysis_ids provided")

    query = {"user_id": str(current_user["_id"])}

    if not delete_all:
        from bson import ObjectId
        oids = []
        for a in ids:
            try:
                oids.append(ObjectId(a))
            except Exception:
                continue
        if not oids:
            raise HTTPException(status_code=400, detail="No valid analysis ids provided")
        query["_id"] = {"$in": oids}

    result = await get_analysis_results_collection().delete_many(query)
    return {"deleted": result.deleted_count}


# ============================================================================
# Bulk / Compare-Resumes endpoint
# ============================================================================

@router.post("/analyze/bulk")
async def analyze_resumes_bulk(
    resume_files: List[UploadFile] = File(..., description="Multiple resume files (PDF or DOCX)"),
    jd_text: Optional[str] = Form(None, description="Job description text (optional if jd_file provided)"),
    jd_file: Optional[UploadFile] = File(None, description="Optional JD file (PDF/DOCX/TXT)"),
    job_title: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
):
    """
    Analyze and rank multiple resumes against a single JD.

    For each resume, runs the full pipeline (parse → match → ATS → role-fit
    → verdict). Returns the candidates sorted best→worst by a composite
    readiness score so a recruiter can immediately see who fits the role best.
    """
    if not resume_files:
        raise HTTPException(status_code=400, detail="At least one resume is required.")
    if len(resume_files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 resumes per comparison.")

    # 1. Resolve JD text (paste OR file)
    if jd_file is not None and getattr(jd_file, "filename", ""):
        try:
            jd_text = await _extract_jd_text_from_file(jd_file)
        finally:
            await jd_file.close()
        if not jd_text:
            raise HTTPException(status_code=400, detail="Could not extract text from JD file.")

    if not jd_text or not jd_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description is required (paste text or upload a JD file).",
        )

    # 2. Parse JD once
    try:
        jd_data = process_job_description(jd_text)
    except Exception:
        logger.exception("Bulk JD parsing failed")
        raise HTTPException(status_code=500, detail="Failed to parse job description")
    if job_title and not jd_data.get("job_title"):
        jd_data["job_title"] = job_title

    # 3. Run pipeline per resume
    candidates = []
    errors = []

    for idx, rf in enumerate(resume_files):
        ext = os.path.splitext(rf.filename or "")[1].lower()
        if ext not in ALLOWED_RESUME_EXT:
            errors.append({"file_name": rf.filename, "error": "Unsupported type (only PDF/DOCX)"})
            continue

        temp_path = None
        try:
            temp_path = await _save_temp_upload(rf)
            file_type = "pdf" if ext == ".pdf" else "docx"
            resume_data = parse_resume(temp_path, file_type)
            if "error" in resume_data:
                errors.append({"file_name": rf.filename, "error": resume_data["error"]})
                continue

            pipeline_result = run_full_analysis(resume_data, jd_data)

            ats_score = float(pipeline_result["ats"]["ats_score"] or 0)
            match_score = float(pipeline_result["match"]["match_score"] or 0)
            top_role = (pipeline_result.get("predicted_roles") or [{}])[0] if pipeline_result.get("predicted_roles") else {}
            role_score = float((top_role or {}).get("score", 0) or 0)

            # Composite readiness — heavier on JD match for hiring comparison
            composite = ats_score * 0.35 + match_score * 0.45 + role_score * 0.20

            candidates.append({
                "candidate_id": uuid.uuid4().hex[:8],
                "file_name": rf.filename,
                "candidate_name": resume_data.get("name") or "Unknown",
                "email": (resume_data.get("additional_info") or {}).get("email"),
                "ats_score": round(ats_score, 2),
                "match_score": round(match_score, 2),
                "role_fit_score": round(role_score, 2),
                "composite_score": round(composite, 2),
                "top_role": (top_role or {}).get("role"),
                "matched_skills": pipeline_result["match"]["matched_skills"],
                "missing_skills": pipeline_result["match"]["missing_skills"],
                "matched_count": pipeline_result["match"]["matched_count"],
                "total_jd_skills": pipeline_result["match"]["total_jd_skills"],
                "verdict": pipeline_result.get("verdict", {}),
                "predicted_roles": pipeline_result.get("predicted_roles", [])[:3],
            })
        except Exception:
            logger.exception("Bulk pipeline failed for %s", rf.filename)
            errors.append({"file_name": rf.filename, "error": "Analysis failed"})
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            try:
                await rf.close()
            except Exception:
                pass

    if not candidates:
        raise HTTPException(
            status_code=400,
            detail={"message": "No resumes could be analyzed.", "errors": errors},
        )

    # 4. Rank best -> worst by composite score
    candidates.sort(key=lambda c: c["composite_score"], reverse=True)
    for rank, c in enumerate(candidates, start=1):
        c["rank"] = rank

    return {
        "job_title": jd_data.get("job_title") or job_title or "Target role",
        "total": len(candidates),
        "errors": errors,
        "jd_summary": {
            "required_skills": jd_data.get("required_skills", []),
            "experience_required": jd_data.get("experience_required"),
            "education_required": jd_data.get("education_required"),
        },
        "candidates": candidates,
    }
