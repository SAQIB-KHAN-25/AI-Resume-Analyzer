from pydantic import BaseModel
from typing import List, Optional


class JDInput(BaseModel):
    """Model for job description input"""
    job_description: str


class JDScoring(BaseModel):
    """Model for JD quality and extraction confidence signals"""
    skill_coverage_pct: float
    top_keyword_density_pct: float
    role_hints: List[str]


class JDData(BaseModel):
    """Model for processed job description data"""
    required_skills: List[str]
    keywords: List[str]
    text_preview: Optional[str] = None
    scoring: Optional[JDScoring] = None


class JDProcessResponse(BaseModel):
    """Model for JD processing response"""
    message: str
    jd_data: Optional[JDData] = None
    jd_id: Optional[str] = None
