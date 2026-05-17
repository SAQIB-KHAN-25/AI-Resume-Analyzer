"""
Pydantic models for the unified analysis pipeline.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PredictedRole(BaseModel):
    role: str
    score: float = 0.0
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)


class MatchSummary(BaseModel):
    match_score: float = 0.0
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    total_jd_skills: int = 0
    matched_count: int = 0


class ATSBreakdown(BaseModel):
    keyword_score: float = 0.0
    skill_score: float = 0.0
    section_score: float = 0.0
    experience_score: float = 0.0
    education_score: float = 0.0
    structure_score: float = 0.0


class ATSSummary(BaseModel):
    ats_score: float = 0.0
    score_category: str = "low"
    score_label: str = "Needs Improvement"
    breakdown: ATSBreakdown = Field(default_factory=ATSBreakdown)
    recommendations: List[str] = Field(default_factory=list)


class AnalysisRequest(BaseModel):
    """Body for /api/analyze when posting JSON (skills already extracted)."""
    resume_id: Optional[str] = None
    jd_text: Optional[str] = None
    jd_id: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Full pipeline response."""
    analysis_id: Optional[str] = None
    resume_id: Optional[str] = None
    jd_id: Optional[str] = None

    resume_data: Dict[str, Any] = Field(default_factory=dict)
    jd_data: Dict[str, Any] = Field(default_factory=dict)

    match: MatchSummary = Field(default_factory=MatchSummary)
    ats: ATSSummary = Field(default_factory=ATSSummary)
    predicted_roles: List[PredictedRole] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    verdict: Dict[str, Any] = Field(default_factory=dict)

    message: str = "Analysis completed successfully"
