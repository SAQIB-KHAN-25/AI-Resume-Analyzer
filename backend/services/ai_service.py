"""
AI Service Module - OpenAI Integration
Provides AI-powered resume analysis features:
- Semantic skill matching
- Resume improvement suggestions
- Role prediction
- Cover letter generation
- Interview question generation
"""

import os
from typing import Dict, List, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize OpenAI client only when key is available.
_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=_api_key) if _api_key else None

# Default model to use
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _call_openai(
    prompt: str,
    system_prompt: str = "You are a professional HR and career advisor.",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1000,
    temperature: float = 0.7
) -> str:
    """
    Make a call to OpenAI API.
    
    Args:
        prompt: User prompt
        system_prompt: System instruction
        model: OpenAI model to use
        max_tokens: Maximum tokens in response
        temperature: Creativity level (0-1)
    
    Returns:
        Response text from OpenAI
    """
    if client is None:
        raise RuntimeError("OpenAI API is not configured")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.exception("OpenAI API call failed")
        raise RuntimeError("OpenAI API call failed") from e


def semantic_skill_match(
    resume_skills: List[str],
    jd_skills: List[str]
) -> Dict[str, Any]:
    """
    Use AI to perform semantic skill matching.
    Understands that "ML" matches "Machine Learning", etc.
    
    Returns:
        Dictionary with semantic matches and analysis
    """
    prompt = f"""Analyze these skills for semantic matches:

RESUME SKILLS: {', '.join(resume_skills)}

JOB REQUIREMENTS: {', '.join(jd_skills)}

For each job requirement, determine if the candidate has an equivalent skill (exact match OR semantic equivalent).
Examples of semantic matches:
- "ML" = "Machine Learning"
- "JS" = "JavaScript"  
- "Data Analysis" ≈ "Data Analytics"
- "React.js" = "React"

Respond in this JSON format:
{{
    "semantic_matches": [
        {{"jd_skill": "skill1", "resume_skill": "matching skill", "match_type": "exact|semantic|partial"}},
        ...
    ],
    "unmatched_jd_skills": ["skill1", "skill2"],
    "transferable_skills": ["resume skills that could partially apply"],
    "match_percentage": 75,
    "analysis": "Brief analysis of skill alignment"
}}

Return ONLY valid JSON, no markdown."""

    response = _call_openai(
        prompt,
        system_prompt="You are a technical recruiter expert at matching skills. Return only valid JSON.",
        temperature=0.3
    )
    
    try:
        import json
        return json.loads(response)
    except Exception:
        return {
            "semantic_matches": [],
            "unmatched_jd_skills": jd_skills,
            "transferable_skills": [],
            "match_percentage": 0,
            "analysis": response,
            "raw_response": response
        }


def generate_resume_improvements(
    resume_data: Dict[str, Any],
    jd_data: Dict[str, Any],
    ats_score: float
) -> Dict[str, Any]:
    """
    Generate AI-powered resume improvement suggestions.
    
    Args:
        resume_data: Parsed resume data
        jd_data: Job description data
        ats_score: Current ATS score
    
    Returns:
        Dictionary with improvement suggestions
    """
    prompt = f"""Analyze this resume against the job description and provide specific improvements:

RESUME DATA:
- Name: {resume_data.get('name', 'Unknown')}
- Skills: {', '.join(resume_data.get('skills', [])[:15])}
- Experience: {resume_data.get('experience', 'Not specified')}
- Education: {resume_data.get('education', 'Not specified')}
- Projects: {resume_data.get('projects', [])}

JOB REQUIREMENTS:
- Required Skills: {', '.join(jd_data.get('skills', [])[:10])}
- Keywords: {', '.join(jd_data.get('keywords', [])[:10])}

CURRENT ATS SCORE: {ats_score}%

Provide specific, actionable improvements in this JSON format:
{{
    "priority_improvements": [
        {{"area": "Skills", "suggestion": "specific suggestion", "impact": "high|medium|low"}},
        ...
    ],
    "keyword_additions": ["keyword1", "keyword2"],
    "skill_gaps_to_address": ["skill1", "skill2"],
    "formatting_tips": ["tip1", "tip2"],
    "estimated_score_boost": 15,
    "quick_wins": ["easy fix 1", "easy fix 2"]
}}

Return ONLY valid JSON."""

    response = _call_openai(
        prompt,
        system_prompt="You are an expert career coach and ATS optimization specialist.",
        temperature=0.5
    )
    
    try:
        import json
        return json.loads(response)
    except Exception:
        return {
            "priority_improvements": [],
            "analysis": response,
            "raw_response": response
        }


def predict_job_roles(
    resume_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Predict suitable job roles based on resume.
    
    Args:
        resume_data: Parsed resume data
    
    Returns:
        Dictionary with predicted roles and fit scores
    """
    skills = resume_data.get('skills', [])[:20]
    experience = resume_data.get('experience', 'Not specified')
    education = resume_data.get('education', 'Not specified')
    projects = resume_data.get('projects', [])[:5]
    
    prompt = f"""Based on this candidate profile, suggest the most suitable job roles:

SKILLS: {', '.join(skills)}
EXPERIENCE: {experience}
EDUCATION: {education}
PROJECTS: {projects}

Suggest 5-7 job roles that would be good fits, ranging from current level to stretch roles.

Respond in this JSON format:
{{
    "predicted_roles": [
        {{
            "title": "Job Title",
            "fit_score": 85,
            "level": "entry|mid|senior|lead",
            "reason": "Why this role fits",
            "skills_aligned": ["skill1", "skill2"],
            "skills_to_develop": ["skill1"]
        }},
        ...
    ],
    "career_path": "Brief career trajectory suggestion",
    "industry_fit": ["Tech", "Finance", "Healthcare"]
}}

Return ONLY valid JSON."""

    response = _call_openai(
        prompt,
        system_prompt="You are a career advisor with deep knowledge of tech industry roles and career paths.",
        temperature=0.6
    )
    
    try:
        import json
        return json.loads(response)
    except Exception:
        return {
            "predicted_roles": [],
            "analysis": response,
            "raw_response": response
        }


def generate_cover_letter(
    resume_data: Dict[str, Any],
    jd_data: Dict[str, Any],
    company_name: str = "the company",
    job_title: str = "this position"
) -> Dict[str, Any]:
    """
    Generate a personalized cover letter.
    
    Args:
        resume_data: Parsed resume data
        jd_data: Job description data
        company_name: Target company name
        job_title: Target job title
    
    Returns:
        Dictionary with generated cover letter
    """
    name = resume_data.get('name', 'Candidate')
    skills = resume_data.get('skills', [])[:10]
    experience = resume_data.get('experience', 'experience')
    jd_skills = jd_data.get('skills', [])[:8]
    
    prompt = f"""Write a professional, compelling cover letter for:

CANDIDATE: {name}
KEY SKILLS: {', '.join(skills)}
EXPERIENCE: {experience}
TARGET COMPANY: {company_name}
TARGET ROLE: {job_title}
REQUIRED SKILLS: {', '.join(jd_skills)}

Write a cover letter that:
1. Opens with a strong hook
2. Highlights relevant experience and skills
3. Shows knowledge of role requirements
4. Demonstrates enthusiasm
5. Ends with a clear call to action

Keep it to 3-4 paragraphs, professional but personable.

Respond in JSON format:
{{
    "cover_letter": "The full cover letter text...",
    "key_points_highlighted": ["point1", "point2"],
    "customization_tips": ["tip1", "tip2"]
}}

Return ONLY valid JSON."""

    response = _call_openai(
        prompt,
        system_prompt="You are an expert career coach who writes compelling cover letters.",
        max_tokens=1500,
        temperature=0.7
    )
    
    try:
        import json
        return json.loads(response)
    except Exception:
        return {
            "cover_letter": response,
            "raw_response": response
        }


def generate_interview_questions(
    jd_data: Dict[str, Any],
    resume_data: Dict[str, Any],
    question_count: int = 10
) -> Dict[str, Any]:
    """
    Generate likely interview questions based on JD and resume.
    
    Args:
        jd_data: Job description data
        resume_data: Resume data for personalization
        question_count: Number of questions to generate
    
    Returns:
        Dictionary with interview questions and tips
    """
    jd_skills = jd_data.get('skills', [])[:10]
    resume_skills = resume_data.get('skills', [])[:10]
    
    prompt = f"""Generate {question_count} likely interview questions for a candidate with these skills:

CANDIDATE SKILLS: {', '.join(resume_skills)}
JOB REQUIRES: {', '.join(jd_skills)}

Include a mix of:
- Technical questions (specific to the skills)
- Behavioral questions (STAR method suitable)
- Problem-solving scenarios
- Culture fit questions

Respond in JSON format:
{{
    "questions": [
        {{
            "question": "The interview question",
            "type": "technical|behavioral|scenario|culture",
            "difficulty": "easy|medium|hard",
            "tip": "Brief tip for answering",
            "related_skill": "skill being assessed"
        }},
        ...
    ],
    "preparation_advice": "General preparation advice"
}}

Return ONLY valid JSON."""

    response = _call_openai(
        prompt,
        system_prompt="You are a senior technical interviewer with experience in hiring.",
        max_tokens=2000,
        temperature=0.6
    )
    
    try:
        import json
        return json.loads(response)
    except Exception:
        return {
            "questions": [],
            "analysis": response,
            "raw_response": response
        }


def analyze_resume_strength(
    resume_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Provide overall resume strength analysis.
    
    Args:
        resume_data: Parsed resume data
    
    Returns:
        Dictionary with strength analysis
    """
    prompt = f"""Analyze this resume for overall strength and marketability:

NAME: {resume_data.get('name', 'Unknown')}
SKILLS: {', '.join(resume_data.get('skills', [])[:15])}
EXPERIENCE: {resume_data.get('experience', 'Not specified')}
EDUCATION: {resume_data.get('education', 'Not specified')}
PROJECTS: {resume_data.get('projects', [])}
CERTIFICATIONS: {resume_data.get('additional_info', {}).get('certifications', [])}

Provide a comprehensive analysis in JSON format:
{{
    "overall_score": 75,
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "market_positioning": "How competitive this profile is",
    "unique_selling_points": ["usp1", "usp2"],
    "experience_level": "entry|junior|mid|senior|lead|executive",
    "primary_domain": "e.g., Backend Development, Data Science",
    "improvement_roadmap": [
        {{"action": "action1", "timeline": "1-3 months", "impact": "high"}}
    ]
}}

Return ONLY valid JSON."""

    response = _call_openai(
        prompt,
        system_prompt="You are a senior career strategist and resume expert.",
        temperature=0.5
    )
    
    try:
        import json
        return json.loads(response)
    except Exception:
        return {
            "analysis": response,
            "raw_response": response
        }


def check_api_status() -> Dict[str, Any]:
    """
    Check if OpenAI API is properly configured and working.
    
    Returns:
        Status dictionary
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return {
            "status": "error",
            "message": "OPENAI_API_KEY not found in environment variables",
            "configured": False
        }
    
    # Try a minimal API call
    try:
        if client is None:
            return {
                "status": "error",
                "message": "OpenAI client is not initialized",
                "configured": False,
            }
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        return {
            "status": "ok",
            "message": "OpenAI API is configured and working",
            "configured": True,
            "model_available": DEFAULT_MODEL
        }
    except Exception as e:
        logger.exception("OpenAI API status check failed")
        return {
            "status": "error",
            "message": "OpenAI API call failed",
            "configured": True,
            "error_details": str(e)
        }
