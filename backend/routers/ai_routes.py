"""
AI Routes - OpenAI-powered endpoints
Provides AI-enhanced resume analysis features
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

from ..services.ai_service import (
    semantic_skill_match,
    generate_resume_improvements,
    predict_job_roles,
    generate_cover_letter,
    generate_interview_questions,
    analyze_resume_strength,
    check_api_status
)


router = APIRouter(prefix="/ai", tags=["AI Features"])
logger = logging.getLogger(__name__)


# ============================================
# Request Models
# ============================================

class SemanticMatchRequest(BaseModel):
    resume_skills: List[str] = Field(description="Skills from resume")
    jd_skills: List[str] = Field(description="Skills from job description")


class ImprovementRequest(BaseModel):
    resume_data: Dict[str, Any] = Field(description="Parsed resume data")
    jd_data: Dict[str, Any] = Field(description="Job description data")
    ats_score: float = Field(default=0, description="Current ATS score")


class RolePredictionRequest(BaseModel):
    resume_data: Dict[str, Any] = Field(description="Parsed resume data")


class CoverLetterRequest(BaseModel):
    resume_data: Dict[str, Any] = Field(description="Parsed resume data")
    jd_data: Dict[str, Any] = Field(description="Job description data")
    company_name: str = Field(default="the company", description="Target company name")
    job_title: str = Field(default="this position", description="Target job title")


class InterviewQuestionsRequest(BaseModel):
    jd_data: Dict[str, Any] = Field(description="Job description data")
    resume_data: Dict[str, Any] = Field(description="Resume data")
    question_count: int = Field(default=10, ge=5, le=20, description="Number of questions")


class ResumeStrengthRequest(BaseModel):
    resume_data: Dict[str, Any] = Field(description="Parsed resume data")


# ============================================
# Endpoints
# ============================================

@router.get("/status")
async def get_ai_status() -> Dict[str, Any]:
    """
    Check AI service status.
    Verifies OpenAI API is configured and working.
    """
    return check_api_status()


@router.post("/semantic-match")
async def get_semantic_match(request: SemanticMatchRequest) -> Dict[str, Any]:
    """
    Perform semantic skill matching using AI.
    
    Unlike exact matching, this understands:
    - Abbreviations (ML = Machine Learning)
    - Synonyms (Data Analytics ≈ Data Analysis)
    - Related skills (React.js = React)
    
    Returns detailed match analysis with percentages.
    """
    try:
        result = semantic_skill_match(request.resume_skills, request.jd_skills)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.exception("AI semantic match failed")
        raise HTTPException(
            status_code=500,
            detail="AI matching failed. Please try again later."
        )


@router.post("/improvements")
async def get_improvements(request: ImprovementRequest) -> Dict[str, Any]:
    """
    Get AI-powered resume improvement suggestions.
    
    Analyzes resume against JD and provides:
    - Priority improvements with impact levels
    - Keywords to add
    - Skill gaps to address
    - Formatting tips
    - Estimated score boost
    """
    try:
        result = generate_resume_improvements(
            request.resume_data,
            request.jd_data,
            request.ats_score
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.exception("AI improvement generation failed")
        raise HTTPException(
            status_code=500,
            detail="Improvement generation failed. Please try again later."
        )


@router.post("/predict-roles")
async def get_role_predictions(request: RolePredictionRequest) -> Dict[str, Any]:
    """
    Predict suitable job roles based on resume.
    
    Returns:
    - 5-7 suitable job roles with fit scores
    - Experience level assessment
    - Career path suggestions
    - Industry fit analysis
    """
    try:
        result = predict_job_roles(request.resume_data)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.exception("AI role prediction failed")
        raise HTTPException(
            status_code=500,
            detail="Role prediction failed. Please try again later."
        )


@router.post("/cover-letter")
async def get_cover_letter(request: CoverLetterRequest) -> Dict[str, Any]:
    """
    Generate a personalized cover letter.
    
    Creates a professional cover letter that:
    - Highlights relevant experience
    - Addresses job requirements
    - Shows company knowledge
    - Includes call to action
    """
    try:
        result = generate_cover_letter(
            request.resume_data,
            request.jd_data,
            request.company_name,
            request.job_title
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.exception("AI cover letter generation failed")
        raise HTTPException(
            status_code=500,
            detail="Cover letter generation failed. Please try again later."
        )


@router.post("/interview-questions")
async def get_interview_questions(request: InterviewQuestionsRequest) -> Dict[str, Any]:
    """
    Generate likely interview questions.
    
    Based on JD and resume, generates:
    - Technical questions
    - Behavioral questions
    - Scenario-based questions
    - Tips for answering each
    """
    try:
        result = generate_interview_questions(
            request.jd_data,
            request.resume_data,
            request.question_count
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.exception("AI interview question generation failed")
        raise HTTPException(
            status_code=500,
            detail="Question generation failed. Please try again later."
        )


@router.post("/resume-strength")
async def get_resume_strength(request: ResumeStrengthRequest) -> Dict[str, Any]:
    """
    Analyze overall resume strength.
    
    Provides:
    - Overall score
    - Strengths and weaknesses
    - Market positioning
    - Unique selling points
    - Improvement roadmap
    """
    try:
        result = analyze_resume_strength(request.resume_data)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.exception("AI resume strength analysis failed")
        raise HTTPException(
            status_code=500,
            detail="Strength analysis failed. Please try again later."
        )


@router.get("/features")
async def get_ai_features() -> Dict[str, Any]:
    """
    Get information about available AI features.
    """
    return {
        "name": "AI-Powered Resume Analysis",
        "version": "1.0.0",
        "powered_by": "OpenAI GPT-3.5",
        "features": [
            {
                "endpoint": "/api/ai/semantic-match",
                "name": "Semantic Skill Matching",
                "description": "AI understands skill synonyms and abbreviations"
            },
            {
                "endpoint": "/api/ai/improvements",
                "name": "Resume Improvements",
                "description": "AI-generated improvement suggestions"
            },
            {
                "endpoint": "/api/ai/predict-roles",
                "name": "Role Prediction",
                "description": "Predict suitable job roles based on profile"
            },
            {
                "endpoint": "/api/ai/cover-letter",
                "name": "Cover Letter Generator",
                "description": "Generate personalized cover letters"
            },
            {
                "endpoint": "/api/ai/interview-questions",
                "name": "Interview Prep",
                "description": "Generate likely interview questions"
            },
            {
                "endpoint": "/api/ai/resume-strength",
                "name": "Resume Strength Analysis",
                "description": "Overall resume quality assessment"
            }
        ]
    }
