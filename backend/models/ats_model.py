"""
ATS Scoring Pydantic Models
Week 5 - Request/Response validation
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ATSScoreRequest(BaseModel):
    """Request model for ATS score calculation."""
    
    resume_keywords: List[str] = Field(
        default=[],
        description="Keywords extracted from resume text"
    )
    jd_keywords: List[str] = Field(
        default=[],
        description="Keywords extracted from job description"
    )
    resume_skills: List[str] = Field(
        default=[],
        description="Technical skills from resume"
    )
    jd_skills: List[str] = Field(
        default=[],
        description="Required skills from job description"
    )
    sections: List[str] = Field(
        default=[],
        description="Resume sections detected (e.g., education, experience, skills)"
    )
    resume_education: List[str] = Field(
        default=[],
        description="Education qualifications from resume"
    )
    required_education: List[str] = Field(
        default=[],
        description="Required education from job description"
    )
    experience_years: float = Field(
        default=0,
        ge=0,
        description="Years of experience from resume"
    )
    required_experience: float = Field(
        default=0,
        ge=0,
        description="Required years of experience from JD"
    )
    resume_text: str = Field(
        default="",
        description="Full resume text for additional analysis"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "resume_keywords": ["python", "developer", "api", "backend"],
                "jd_keywords": ["python", "developer", "api", "docker", "aws"],
                "resume_skills": ["Python", "SQL", "React", "FastAPI"],
                "jd_skills": ["Python", "SQL", "Docker", "AWS"],
                "sections": ["education", "experience", "skills", "projects"],
                "resume_education": ["B.Tech", "Computer Science"],
                "required_education": ["Bachelor"],
                "experience_years": 3,
                "required_experience": 2,
                "resume_text": "John Doe\nSoftware Developer with 3 years experience..."
            }
        }


class ScoreBreakdown(BaseModel):
    """Individual score components."""
    keyword_score: float
    skill_score: float
    section_score: float
    experience_score: float
    education_score: float
    structure_score: float


class MatchDetails(BaseModel):
    """Details for a matching category."""
    matched: List[str]
    missing: List[str]
    match_rate: Optional[str] = None
    note: Optional[str] = None


class RecommendationItem(BaseModel):
    """Single recommendation item."""
    area: str
    issue: str
    action: str


class Recommendations(BaseModel):
    """Recommendations based on ATS analysis."""
    overall_assessment: str
    strengths: List[str]
    critical_improvements: List[RecommendationItem]
    important_improvements: List[RecommendationItem]
    suggestions: List[RecommendationItem]
    improvement_potential: float


class ATSScoreResponse(BaseModel):
    """Response model for ATS score calculation."""
    
    ats_score: float = Field(
        description="Final ATS score (0-100)"
    )
    score_category: str = Field(
        description="Score category: excellent, good, moderate, or low"
    )
    score_label: str = Field(
        description="Human-readable score label"
    )
    breakdown: Dict[str, float] = Field(
        description="Individual component scores"
    )
    weights: Dict[str, str] = Field(
        description="Weight distribution for scoring"
    )
    details: Dict[str, Any] = Field(
        description="Detailed match information"
    )
    analysis: Dict[str, Any] = Field(
        description="Additional analysis (length, format, density)"
    )
    recommendations: Dict[str, Any] = Field(
        description="Actionable improvement recommendations"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "ats_score": 72.5,
                "score_category": "good",
                "score_label": "Good Match",
                "breakdown": {
                    "keyword_score": 80.0,
                    "skill_score": 66.67,
                    "section_score": 75.0,
                    "experience_score": 100.0,
                    "education_score": 100.0,
                    "structure_score": 85.0
                },
                "weights": {
                    "keyword": "45%",
                    "skill": "25%",
                    "section": "15%",
                    "experience": "15%"
                },
                "details": {},
                "analysis": {},
                "recommendations": {}
            }
        }


class SimpleATSRequest(BaseModel):
    """Simplified request when full data isn't available."""
    
    resume_skills: List[str] = Field(
        description="Skills extracted from resume"
    )
    jd_skills: List[str] = Field(
        description="Skills from job description"
    )
    match_score: Optional[float] = Field(
        default=None,
        description="Pre-calculated match score from Week 4"
    )
    resume_text: Optional[str] = Field(
        default="",
        description="Resume text for length/format analysis"
    )
    sections: List[str] = Field(
        default=["skills"],
        description="Detected resume sections"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "resume_skills": ["Python", "SQL", "React"],
                "jd_skills": ["Python", "SQL", "Docker"],
                "match_score": 66.67,
                "resume_text": "Software developer resume...",
                "sections": ["skills", "experience", "education"]
            }
        }
