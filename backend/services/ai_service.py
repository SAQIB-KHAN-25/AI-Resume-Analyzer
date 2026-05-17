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
import json
import re
from typing import Dict, List, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────
# Provider configuration
# ─────────────────────────────────────────────────────────────────────────
# AI_PROVIDER: "auto" (default — OpenAI first, Gemini fallback),
#              "openai" (force OpenAI only),
#              "gemini" (force Gemini only).
AI_PROVIDER = (os.getenv("AI_PROVIDER") or "auto").strip().lower()

# OpenAI
_openai_api_key = os.getenv("OPENAI_API_KEY")
try:
    client = OpenAI(api_key=_openai_api_key) if _openai_api_key else None
except TypeError as exc:
    logger.warning("OpenAI client initialization failed; disabling OpenAI features: %s", exc)
    client = None
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Gemini (Google AI Studio) — called via REST so we don't depend on the
# google-generativeai SDK (which has protobuf issues on newer Pythons).
_gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_API_BASE = os.getenv(
    "GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta"
)
# Truthy sentinel used in place of an SDK client object.
_gemini_client = bool(_gemini_api_key)
if _gemini_client:
    logger.info("Gemini provider enabled (model=%s, transport=REST)", GEMINI_MODEL)

if client is None and not _gemini_client:
    logger.warning(
        "No AI provider configured. Set OPENAI_API_KEY and/or GEMINI_API_KEY in .env"
    )


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


# ─────────────────────────────────────────────────────────────────────────
# Unified LLM call with provider failover (OpenAI ⇄ Gemini)
# ─────────────────────────────────────────────────────────────────────────

class _NoProviderError(RuntimeError):
    """Raised when no LLM provider is configured at all."""


def _is_recoverable_provider_error(exc: BaseException) -> bool:
    """Return True if the error looks transient/quota-ish — worth trying the
    next provider. We deliberately keep this broad: better to fail-over than
    to surface a 500 to the user."""
    msg = str(exc).lower()
    return any(
        kw in msg
        for kw in (
            "insufficient_quota",
            "rate limit",
            "rate_limit",
            "quota",
            "exceeded",
            "429",
            "503",
            "502",
            "timeout",
            "temporarily",
            "service unavailable",
        )
    ) or exc.__class__.__name__ in (
        "RateLimitError",
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
    )


def _openai_chat(
    messages: List[Dict[str, str]],
    *,
    max_tokens: int = 1000,
    temperature: float = 0.6,
    json_mode: bool = False,
) -> str:
    if client is None:
        raise RuntimeError("OpenAI not configured")
    kwargs: Dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return (response.choices[0].message.content or "").strip()


def _gemini_chat(
    messages: List[Dict[str, str]],
    *,
    max_tokens: int = 1000,
    temperature: float = 0.6,
    json_mode: bool = False,
) -> str:
    """Call Gemini via its REST endpoint. Avoids the google-generativeai
    SDK so we stay compatible with newer Python versions."""
    if not _gemini_client or not _gemini_api_key:
        raise RuntimeError("Gemini not configured")

    import requests  # local import — keeps module load cheap

    # Gemini has no "system" role. Merge any system messages into the first
    # user turn so behaviour matches OpenAI.
    system_chunks: List[str] = []
    contents: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            system_chunks.append(content)
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})
        else:
            contents.append({"role": "user", "parts": [{"text": content}]})

    if not contents:
        contents.append({
            "role": "user",
            "parts": [{"text": " ".join(system_chunks) or "Hello"}],
        })
    elif system_chunks:
        first = contents[0]
        existing = first["parts"][0]["text"] if first["parts"] else ""
        first["parts"] = [{
            "text": "\n\n".join(system_chunks) + "\n\n" + existing,
        }]

    generation_config: Dict[str, Any] = {
        "maxOutputTokens": max_tokens,
        "temperature": temperature,
        # Disable hidden "thinking" tokens on Gemini 2.5+ so the entire
        # budget is spent on the visible response.
        "thinkingConfig": {"thinkingBudget": 0},
    }
    if json_mode:
        generation_config["responseMimeType"] = "application/json"

    url = f"{GEMINI_API_BASE}/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": contents,
        "generationConfig": generation_config,
    }

    try:
        resp = requests.post(
            url,
            params={"key": _gemini_api_key},
            json=payload,
            timeout=60,
        )
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Gemini network error: {exc}") from exc

    if resp.status_code != 200:
        # Surface a useful error message (without leaking the API key).
        try:
            err = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            err = resp.text[:200]
        raise RuntimeError(f"Gemini HTTP {resp.status_code}: {err}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise RuntimeError(f"Gemini non-JSON response: {exc}") from exc

    # Walk the response shape defensively. Different finish reasons / model
    # versions return slightly different structures.
    candidates = data.get("candidates") or []
    text_chunks: List[str] = []
    finish_reason = ""
    for cand in candidates:
        finish_reason = cand.get("finishReason") or finish_reason
        parts = ((cand.get("content") or {}).get("parts")) or []
        for part in parts:
            t = part.get("text")
            if isinstance(t, str) and t.strip():
                text_chunks.append(t)

    text = "".join(text_chunks).strip()
    if not text:
        # Surface a useful diagnostic (e.g. SAFETY, MAX_TOKENS, RECITATION)
        raise RuntimeError(
            f"Gemini returned no text (finishReason={finish_reason or 'unknown'})"
        )
    return text


def _call_llm(
    messages: List[Dict[str, str]],
    *,
    max_tokens: int = 1000,
    temperature: float = 0.6,
    json_mode: bool = False,
) -> str:
    """
    Unified LLM call honouring AI_PROVIDER:
      - "openai" → OpenAI only.
      - "gemini" → Gemini only.
      - "auto"   → OpenAI first; on transient/quota error, fall back to Gemini.
                   If only one provider is configured, that one is used.
    """
    have_openai = client is not None
    have_gemini = bool(_gemini_client)

    if not have_openai and not have_gemini:
        raise _NoProviderError("No LLM provider configured")

    # Forced provider
    if AI_PROVIDER == "openai" and have_openai:
        return _openai_chat(messages, max_tokens=max_tokens,
                            temperature=temperature, json_mode=json_mode)
    if AI_PROVIDER == "gemini" and have_gemini:
        return _gemini_chat(messages, max_tokens=max_tokens,
                            temperature=temperature, json_mode=json_mode)

    # Auto mode (or forced provider that's not actually configured → degrade gracefully)
    last_exc: Optional[BaseException] = None
    if have_openai:
        try:
            return _openai_chat(messages, max_tokens=max_tokens,
                                temperature=temperature, json_mode=json_mode)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if not have_gemini or not _is_recoverable_provider_error(exc):
                # No fallback available, or it's a real bug — re-raise.
                raise
            logger.warning(
                "OpenAI call failed (%s) — falling back to Gemini.", exc.__class__.__name__
            )

    if have_gemini:
        try:
            return _gemini_chat(messages, max_tokens=max_tokens,
                                temperature=temperature, json_mode=json_mode)
        except Exception as exc:  # noqa: BLE001
            if last_exc is not None:
                logger.exception("Gemini fallback also failed")
            raise

    # Shouldn't reach here
    if last_exc:
        raise last_exc
    raise _NoProviderError("No usable LLM provider")


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


# ─────────────────────────────────────────────────────────────────────────────
# Role Explorer (career roadmap for any job title)
# ─────────────────────────────────────────────────────────────────────────────

ROLE_GUIDE_SYSTEM = (
    "You are a senior career coach and technical recruiter. "
    "Return concise, structured JSON ONLY. No markdown, no commentary."
)


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Try to safely extract a JSON object from a possibly noisy LLM response.
    """
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    # Strip ``` fences
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S | re.I)
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            pass
    # Find first {...} block
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    raise ValueError("Model did not return valid JSON")


def _coerce_string_list(value: Any, limit: int = 12) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            # Sometimes the model nests a {"name": "Python"} shape.
            name = item.get("name") or item.get("title") or item.get("skill")
            if isinstance(name, str) and name.strip():
                out.append(name.strip())
        if len(out) >= limit:
            break
    return out


def _coerce_learning_path(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    steps: List[Dict[str, Any]] = []
    for idx, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("name") or item.get("step_title")
        if not title:
            continue
        steps.append({
            "step": int(item.get("step") or idx),
            "title": str(title).strip(),
            "duration": str(item.get("duration") or "").strip(),
            "description": str(item.get("description") or "").strip(),
            "resources": _coerce_string_list(item.get("resources"), limit=6),
        })
        if len(steps) >= 8:
            break
    return steps


def generate_role_guide(role: str) -> Dict[str, Any]:
    """
    Produce a structured career roadmap for a given job role.

    Returns a dict shaped like:
        {
          "role": str,
          "summary": str,
          "key_skills": [str, ...],
          "tools": [str, ...],
          "requirements": [str, ...],
          "learning_path": [{step, title, duration, description, resources[]}],
          "estimated_time": str,
          "career_growth": [str, ...],
          "source": "ai" | "fallback"
        }
    """
    cleaned = (role or "").strip()
    if not cleaned:
        raise ValueError("Role is required")
    if len(cleaned) > 80:
        cleaned = cleaned[:80]

    if client is None and not _gemini_client:
        return _role_guide_fallback(cleaned, reason="No AI provider configured")

    prompt = f"""Build a beginner-friendly career roadmap for the role: "{cleaned}".

Return ONLY a JSON object with EXACTLY these keys:
- "summary": one short paragraph (max 60 words) describing what this role does day-to-day.
- "key_skills": array of 6-10 core skills (strings).
- "tools": array of 5-10 commonly used tools/technologies/frameworks (strings).
- "requirements": array of 4-6 typical hiring requirements (strings, complete sentences).
- "learning_path": ordered array of 4-6 steps. Each step is an object with:
    - "step" (1-based integer)
    - "title" (short action)
    - "duration" (e.g. "2 weeks", "1-2 months")
    - "description" (1-2 sentence explanation)
    - "resources" (array of 2-4 concrete resource names, e.g. "Coursera: Python for Everybody", "freeCodeCamp", "Book: Designing Data-Intensive Applications")
- "estimated_time": realistic total time to become job-ready as a string (e.g. "6-9 months").
- "career_growth": array of 3-5 likely next-step roles or specializations.

Keep it practical, opinionated, and free of fluff. No markdown, JSON only."""

    try:
        raw = _call_llm(
            [
                {"role": "system", "content": ROLE_GUIDE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1400,
            temperature=0.4,
            json_mode=True,
        )
    except Exception as exc:
        logger.exception("Role guide generation failed for role=%s", cleaned)
        return _role_guide_fallback(cleaned, reason=f"AI error: {exc}")

    try:
        data = _extract_json(raw)
    except ValueError:
        logger.warning("Role guide returned non-JSON text for role=%s", cleaned)
        return _role_guide_fallback(cleaned, reason="Model returned non-JSON")

    return {
        "role": cleaned,
        "summary": str(data.get("summary") or "").strip(),
        "key_skills": _coerce_string_list(data.get("key_skills"), limit=12),
        "tools": _coerce_string_list(data.get("tools"), limit=12),
        "requirements": _coerce_string_list(data.get("requirements"), limit=8),
        "learning_path": _coerce_learning_path(data.get("learning_path")),
        "estimated_time": str(data.get("estimated_time") or "").strip(),
        "career_growth": _coerce_string_list(data.get("career_growth"), limit=6),
        "source": "ai",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Role Coach (multi-turn chat for personalized roadmap based on known skills)
# ─────────────────────────────────────────────────────────────────────────────

ROLE_COACH_SYSTEM = (
    "You are an expert career coach and curriculum designer. The user tells you "
    "their target role and the skills/topics they already know. Your job is to "
    "produce a CLEAR, GAP-FOCUSED, ACTIONABLE plan.\n\n"
    "If the target role OR the current skills are unclear, ask ONE specific "
    "clarifying question and STOP. Otherwise, respond using EXACTLY this "
    "markdown structure (keep the section headings literally):\n\n"
    "## What you already have\n"
    "One short sentence summarising the user's current skills and how far "
    "they get them toward the target role (e.g. \"Solid MERN backend basics — "
    "roughly 40% of the way to a Junior Full Stack role\").\n\n"
    "## Missing skills (priority order)\n"
    "A numbered list of the 4-7 most important gaps for the target role. For "
    "each gap use this exact format on ONE line:\n"
    "`N. **<Skill name>** — <one-line reason it matters for this role>`\n\n"
    "## Learning plan\n"
    "For EACH missing skill above, output a sub-section in the same order, "
    "using exactly this template:\n\n"
    "### N. <Skill name>\n"
    "- **Goal:** what \"good enough\" looks like in 1 sentence.\n"
    "- **Time:** realistic estimate, e.g. `2 weeks`, `1 month`.\n"
    "- **Learn from:** 1-3 specific, real resources "
    "(course name, official docs, YouTube channel, book). Use links when "
    "obvious, e.g. `[freeCodeCamp](https://www.freecodecamp.org)`.\n"
    "- **Practice:** ONE concrete mini-project or exercise to lock it in.\n\n"
    "## Capstone project\n"
    "One paragraph describing a single portfolio-grade project that "
    "exercises BOTH the user's existing skills AND the new ones, with the "
    "stack named explicitly.\n\n"
    "## Next action (today)\n"
    "One imperative sentence telling the user the very next thing to do in "
    "the next 60 minutes.\n\n"
    "Hard rules:\n"
    "- Always include a \"## Missing skills\" section with at least 3 items.\n"
    "- Be SPECIFIC. Never say things like \"learn more about X\" — say WHAT "
    "to learn, WHERE, and FOR HOW LONG.\n"
    "- Recommend real, well-known resources. NEVER invent fake course names.\n"
    "- Don't repeat the user's skill list back at them; reference it briefly.\n"
    "- Keep the whole response under 550 words. No fluff, no disclaimers."
)


def role_coach_reply(messages: List[Dict[str, str]]) -> str:
    """
    Run a coaching chat turn.

    `messages` is a list of dicts shaped like [{"role": "user"|"assistant",
    "content": "..."}, ...]. We prepend our system prompt.

    Returns the assistant's reply as a markdown string.
    """
    if not messages:
        raise ValueError("messages cannot be empty")

    if client is None and not _gemini_client:
        return _role_coach_fallback(messages)

    chat = [{"role": "system", "content": ROLE_COACH_SYSTEM}]
    # Trim to last 12 turns to keep token usage bounded
    for m in messages[-12:]:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            chat.append({"role": role, "content": content})

    try:
        return _call_llm(chat, max_tokens=900, temperature=0.5)
    except Exception as exc:
        logger.exception("Role coach reply failed")
        return _role_coach_fallback(messages, reason=str(exc))


# Curated, role-specific gap libraries used by the offline fallback so even
# without OpenAI the user gets a useful, structured, gap-focused plan.
_ROLE_GAP_LIBRARY: Dict[str, List[Dict[str, str]]] = {
    "full stack": [
        {
            "skill": "React (or another modern UI framework)",
            "why": "Almost every full-stack job uses a component-based UI framework.",
            "goal": "Build a SPA with routing, hooks, and a shared component library.",
            "time": "3-4 weeks",
            "learn_from": "[React docs](https://react.dev/learn), [Full Stack Open](https://fullstackopen.com), Scrimba React course",
            "practice": "Rebuild a small Express+Mongo CRUD app you already have with a React front-end.",
        },
        {
            "skill": "TypeScript",
            "why": "Industry standard for production-grade Node/React codebases.",
            "goal": "Type a small React+Express project end-to-end without `any`.",
            "time": "2 weeks",
            "learn_from": "[TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html), Matt Pocock's `Total TypeScript` basics",
            "practice": "Convert one of your existing JS files to strict TS.",
        },
        {
            "skill": "REST API design + auth (JWT / sessions)",
            "why": "Hiring managers test API design, status codes, and auth flow knowledge.",
            "goal": "Design a clean REST API with login, refresh tokens, and protected routes.",
            "time": "1-2 weeks",
            "learn_from": "[MDN HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP), Hussein Nasser's API videos, `Express` docs",
            "practice": "Add JWT auth + role-based access control to your existing MERN app.",
        },
        {
            "skill": "Testing (Jest + React Testing Library)",
            "why": "Almost every team requires automated tests for new code.",
            "goal": "Comfortable writing unit, integration, and basic E2E tests.",
            "time": "1-2 weeks",
            "learn_from": "[Testing Library docs](https://testing-library.com/docs/), Kent C. Dodds' free Epic React intros",
            "practice": "Add 10 tests to your portfolio project — 5 backend, 5 React.",
        },
        {
            "skill": "Git workflows + deployment (CI/CD)",
            "why": "Day-1 expectation: branches, PRs, and shipping to a hosted environment.",
            "goal": "Push code that auto-deploys via GitHub Actions to Vercel/Render.",
            "time": "1 week",
            "learn_from": "[GitHub Actions docs](https://docs.github.com/en/actions), Fireship CI/CD videos",
            "practice": "Set up a Vercel + Render pipeline for your portfolio app.",
        },
        {
            "skill": "Data modeling + indexing (Mongo / SQL)",
            "why": "Junior devs are often filtered out for poor schema/index decisions.",
            "goal": "Design schemas for a non-trivial domain and explain index trade-offs.",
            "time": "1 week",
            "learn_from": "[MongoDB University M001+M201](https://learn.mongodb.com/), `Use The Index, Luke`",
            "practice": "Profile your slowest endpoint and add the right index.",
        },
    ],
    "data scientist": [
        {
            "skill": "Statistics & probability fundamentals",
            "why": "Interviews lean heavily on hypothesis testing, distributions, and A/B tests.",
            "goal": "Comfortable explaining p-values, CLT, and confidence intervals out loud.",
            "time": "3 weeks",
            "learn_from": "StatQuest YouTube channel, `Think Stats` (free book), Khan Academy stats",
            "practice": "Run an A/B test on any public dataset and write a 1-page report.",
        },
        {
            "skill": "Pandas + scikit-learn",
            "why": "These two libraries cover ~80% of day-1 data science work.",
            "goal": "Build an end-to-end ML pipeline: load → clean → feature → model → evaluate.",
            "time": "3-4 weeks",
            "learn_from": "[Kaggle Learn](https://www.kaggle.com/learn), `Hands-On ML` (Géron) Ch. 1-3",
            "practice": "Publish one Kaggle notebook with a tuned model + clear write-up.",
        },
        {
            "skill": "SQL for analytics",
            "why": "Every DS job tests window functions and CTEs in screens.",
            "goal": "Solve medium SQL window-function problems in under 5 minutes.",
            "time": "2 weeks",
            "learn_from": "[Mode Analytics SQL tutorial](https://mode.com/sql-tutorial/), `StrataScratch` free tier",
            "practice": "Finish 30 medium-difficulty SQL problems on StrataScratch or LeetCode.",
        },
        {
            "skill": "Storytelling with data + visualisation",
            "why": "DS work only matters if stakeholders understand it.",
            "goal": "Produce a 1-page narrative chart from raw data that a PM can read in 60 seconds.",
            "time": "1-2 weeks",
            "learn_from": "`Storytelling with Data` (Knaflic), Matplotlib + seaborn docs",
            "practice": "Rewrite the report from your A/B test as a single dashboard.",
        },
        {
            "skill": "Production basics (Git, Docker, deploy a model)",
            "why": "Most teams want DS who can ship, not just notebook.",
            "goal": "Wrap a model in a FastAPI endpoint and run it in Docker.",
            "time": "1-2 weeks",
            "learn_from": "[FastAPI docs](https://fastapi.tiangolo.com/), Docker's `Get Started` guide",
            "practice": "Deploy your Kaggle model behind `/predict` and call it from a script.",
        },
    ],
    "devops": [
        {
            "skill": "Linux + shell scripting (bash)",
            "why": "Every DevOps interview opens with command-line questions.",
            "goal": "Comfortable writing scripts with pipes, traps, and error handling.",
            "time": "2 weeks",
            "learn_from": "[The Missing Semester](https://missing.csail.mit.edu/), `Linux Journey`",
            "practice": "Automate one repetitive task on your machine with a single bash script.",
        },
        {
            "skill": "Containers (Docker) and Kubernetes basics",
            "why": "Containers are the lingua franca of modern infrastructure.",
            "goal": "Build, push, and run a multi-container app locally; deploy it to a minikube cluster.",
            "time": "3-4 weeks",
            "learn_from": "Docker `Get Started`, [KodeKloud Kubernetes for the Absolute Beginners](https://kodekloud.com)",
            "practice": "Containerise an app and write a working Helm chart for it.",
        },
        {
            "skill": "Infrastructure as Code (Terraform)",
            "why": "Teams expect IaC for any non-toy cloud resource.",
            "goal": "Provision a VPC + ECS/EKS cluster with reusable Terraform modules.",
            "time": "2-3 weeks",
            "learn_from": "[Terraform docs](https://developer.hashicorp.com/terraform/tutorials), `Terraform Up & Running` (Brikman)",
            "practice": "Recreate your manually-built AWS sandbox using Terraform only.",
        },
        {
            "skill": "CI/CD pipelines",
            "why": "Day-1 expectation: ship code safely on every push.",
            "goal": "Build a pipeline with tests, build, container push, and gated deploy.",
            "time": "1-2 weeks",
            "learn_from": "[GitHub Actions docs](https://docs.github.com/en/actions), GitLab CI tutorials",
            "practice": "Add a green-build badge + deploy step to any project on your GitHub.",
        },
        {
            "skill": "Observability (logging, metrics, tracing)",
            "why": "Senior DevOps engineers are paid for understanding production, not provisioning.",
            "goal": "Understand the difference between logs/metrics/traces and when to use each.",
            "time": "1-2 weeks",
            "learn_from": "Grafana Labs YouTube, [OpenTelemetry docs](https://opentelemetry.io/docs/)",
            "practice": "Wire Prometheus + Grafana into your minikube app and graph one SLO.",
        },
    ],
    "ml engineer": [
        {
            "skill": "Strong Python + software engineering basics",
            "why": "ML eng is 60% engineering; sloppy code is the #1 rejection reason.",
            "goal": "Write modular, typed, tested Python you'd be proud to PR.",
            "time": "3 weeks",
            "learn_from": "`Fluent Python` (Ramalho), Real Python tutorials",
            "practice": "Refactor any of your existing notebooks into a clean package with tests.",
        },
        {
            "skill": "ML system design",
            "why": "Senior ML interviews are dominated by system-design rounds.",
            "goal": "Confidently sketch a recommender / search / fraud system on a whiteboard.",
            "time": "3-4 weeks",
            "learn_from": "`Designing ML Systems` (Chip Huyen), `Machine Learning Design Interview` (Aminian)",
            "practice": "Write up 3 mock ML system designs as blog posts.",
        },
        {
            "skill": "Model serving + MLOps",
            "why": "Models are worthless until they serve traffic.",
            "goal": "Serve a model behind FastAPI, containerised, with basic monitoring.",
            "time": "2 weeks",
            "learn_from": "Made With ML MLOps course, [FastAPI docs](https://fastapi.tiangolo.com/)",
            "practice": "Deploy a HuggingFace model behind `/predict` with a latency SLO.",
        },
        {
            "skill": "Deep learning fundamentals (PyTorch)",
            "why": "Even non-DL teams ask about backprop, optimisation, regularisation.",
            "goal": "Train and fine-tune a small transformer on a custom dataset.",
            "time": "3-4 weeks",
            "learn_from": "[Karpathy's Zero to Hero](https://www.youtube.com/playlist?list=PLAqhIrjkxbuWI23v9cThsA9GvCAUhRvKZ), `Deep Learning with PyTorch` (Stevens et al.)",
            "practice": "Fine-tune a small LLM on a domain-specific dataset and write up results.",
        },
    ],
    "product manager": [
        {
            "skill": "Product discovery + user research",
            "why": "The #1 differentiator vs. project managers — actually finding problems worth solving.",
            "goal": "Run 5 customer interviews and synthesize them into a problem brief.",
            "time": "2-3 weeks",
            "learn_from": "`Continuous Discovery Habits` (Teresa Torres), `The Mom Test` (Rob Fitzpatrick)",
            "practice": "Interview 5 real users of any app you use daily and write a 1-page problem statement.",
        },
        {
            "skill": "Metrics + analytics fluency",
            "why": "PMs must define, measure, and defend the right success metrics.",
            "goal": "Confidently define North Star metrics, leading vs lagging indicators.",
            "time": "2 weeks",
            "learn_from": "Reforge PM Fundamentals, Lenny's Newsletter analytics deep-dives",
            "practice": "Pick any consumer app and write its metric tree on one page.",
        },
        {
            "skill": "Basic SQL + experimentation",
            "why": "Modern PMs pull their own data; A/B testing is table stakes.",
            "goal": "Pull metrics from a warehouse and design a basic A/B test.",
            "time": "2 weeks",
            "learn_from": "[Mode SQL tutorial](https://mode.com/sql-tutorial/), `Trustworthy Online Controlled Experiments` (Kohavi)",
            "practice": "Take an open dataset and design a believable A/B test on it.",
        },
        {
            "skill": "Strategy + roadmapping",
            "why": "Senior PMs are paid for prioritisation, not feature lists.",
            "goal": "Articulate a 1-year strategy that ties to company goals.",
            "time": "2-3 weeks",
            "learn_from": "`Good Strategy Bad Strategy` (Rumelt), `Inspired` (Cagan)",
            "practice": "Write a public PM strategy doc for any consumer product.",
        },
    ],
}

# Generic gaps used when no role matches the library.
_DEFAULT_GAPS = [
    {
        "skill": "Domain-relevant project work",
        "why": "Recruiters filter primarily on demonstrable, recent project work.",
        "goal": "Ship one complete project relevant to the target role.",
        "time": "1 month",
        "learn_from": "GitHub, your role's official docs, a well-rated course (Coursera/Udemy/freeCodeCamp)",
        "practice": "Pick a real problem you have, build the smallest version that solves it, ship it.",
    },
    {
        "skill": "Communication of your work",
        "why": "Hiring decisions are made on stories, not bullet points.",
        "goal": "Be able to explain your project in 60 seconds and again in 5 minutes.",
        "time": "1 week",
        "learn_from": "`Made to Stick` (Heath), STAR interview format guides",
        "practice": "Record yourself explaining your project twice — once short, once long.",
    },
    {
        "skill": "Interview preparation",
        "why": "Most candidates lose offers in interviews, not on paper.",
        "goal": "Comfortable solving role-relevant problems out loud.",
        "time": "3-4 weeks",
        "learn_from": "Pramp (free mock interviews), LeetCode patterns, Glassdoor interview reviews",
        "practice": "Do 1 mock interview per week and write down what you missed.",
    },
    {
        "skill": "Job search hygiene",
        "why": "5-10 tailored applications beat 100 generic ones.",
        "goal": "A tracker, a tailored resume per role, and at least 1 referral conversation/week.",
        "time": "Ongoing",
        "learn_from": "LinkedIn search filters, `Ask a Manager` blog, a Notion/Sheets tracker",
        "practice": "Apply to 5 roles tonight, tailoring resume bullets for each.",
    },
]


_ROLE_KEYWORDS = [
    ("full stack", ["full stack", "fullstack", "full-stack", "mern", "mean"]),
    ("data scientist", ["data scientist", "data science", "ml ", "machine learning", "data analyst"]),
    ("devops", ["devops", "dev ops", "sre", "site reliability", "platform engineer", "cloud engineer"]),
    ("ml engineer", ["ml engineer", "ml engineering", "machine learning engineer", "ai engineer"]),
    ("product manager", ["product manager", "product management", "pm role", "associate product"]),
]


def _detect_target_role(text: str) -> Optional[str]:
    lowered = (text or "").lower()
    for key, needles in _ROLE_KEYWORDS:
        if any(n in lowered for n in needles):
            return key
    return None


def _extract_known_skills(text: str) -> List[str]:
    """Very small heuristic — pulls a comma/and-separated skill list out of the user's message."""
    import re as _re
    lowered = (text or "").strip()
    if not lowered:
        return []
    # Look for phrases like "i know X, Y, Z" or "i have X, Y, Z"
    m = _re.search(
        r"\b(?:i\s+(?:know|have|am\s+familiar\s+with|use)|familiar\s+with|comfortable\s+with)\s+(.+?)(?:\.|\n|$)",
        lowered,
        _re.IGNORECASE,
    )
    if not m:
        return []
    chunk = m.group(1)
    # Replace " and " with comma for simpler splitting
    chunk = _re.sub(r"\s+and\s+", ",", chunk, flags=_re.IGNORECASE)
    parts = [p.strip(" .") for p in chunk.split(",")]
    return [p for p in parts if 1 < len(p) < 40][:10]


def _role_coach_fallback(messages: List[Dict[str, str]], reason: str = "") -> str:
    """Useful, gap-focused canned reply when OpenAI is unavailable. Mirrors the
    same structure the live model is asked to produce."""
    last_user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        "",
    )

    note = ""
    if reason and "quota" in reason.lower():
        note = "_(AI temporarily unavailable — showing a curated offline plan.)_\n\n"
    elif reason:
        note = "_(AI unavailable — curated offline plan below.)_\n\n"

    role_key = _detect_target_role(last_user)
    known = _extract_known_skills(last_user)
    role_label = {
        "full stack": "Full Stack Developer",
        "data scientist": "Data Scientist",
        "devops": "DevOps Engineer",
        "ml engineer": "ML Engineer",
        "product manager": "Product Manager",
    }.get(role_key or "", "your target role")

    gaps = _ROLE_GAP_LIBRARY.get(role_key, _DEFAULT_GAPS) if role_key else _DEFAULT_GAPS

    # "What you already have"
    if known:
        have_line = (
            f"You already know **{', '.join(known)}** — a solid foundation for "
            f"{role_label}. The plan below closes the highest-impact gaps."
        )
    else:
        have_line = (
            f"I couldn't reliably parse a skill list, so this plan assumes a "
            f"general beginner-to-mid level toward {role_label}. Reply with the "
            "skills you already know and I'll tighten it."
        )

    # "## Missing skills" — one-liners
    missing_lines = []
    for i, gap in enumerate(gaps, start=1):
        missing_lines.append(f"{i}. **{gap['skill']}** — {gap['why']}")

    # "## Learning plan" — per skill
    plan_sections = []
    for i, gap in enumerate(gaps, start=1):
        plan_sections.append(
            f"### {i}. {gap['skill']}\n"
            f"- **Goal:** {gap['goal']}\n"
            f"- **Time:** `{gap['time']}`\n"
            f"- **Learn from:** {gap['learn_from']}\n"
            f"- **Practice:** {gap['practice']}"
        )

    capstone = (
        f"Build one portfolio-grade project that combines your existing skills "
        f"with at least three of the gaps above. Ship it to GitHub with a clean "
        f"README, a 60-second demo video, and one production deploy. For "
        f"**{role_label}**, prioritise depth in 1-2 areas over breadth across all six."
    )

    next_action = (
        f"Open the **Learn from** link for *step 1* above and spend the next 60 "
        f"minutes on its first lesson — then reply here with what you learned."
    )

    return (
        f"{note}"
        "## What you already have\n"
        f"{have_line}\n\n"
        "## Missing skills (priority order)\n"
        + "\n".join(missing_lines)
        + "\n\n## Learning plan\n"
        + "\n\n".join(plan_sections)
        + "\n\n## Capstone project\n"
        + capstone
        + "\n\n## Next action (today)\n"
        + next_action
    )


def _role_guide_fallback(role: str, reason: str = "") -> Dict[str, Any]:
    """Generic, non-AI fallback so the UI still has something useful to render."""
    return {
        "role": role,
        "summary": (
            f"A {role} is a professional role that combines domain expertise with "
            "modern tooling. The exact responsibilities vary by company and seniority, "
            "but the day-to-day usually involves solving problems, collaborating "
            "across teams, and shipping measurable outcomes."
        ),
        "key_skills": [
            "Strong fundamentals in the core domain",
            "Problem solving and analytical thinking",
            "Communication and collaboration",
            "Version control (Git)",
            "Documentation",
        ],
        "tools": ["Git/GitHub", "VS Code or equivalent IDE", "Slack / Notion", "Jira"],
        "requirements": [
            f"A foundational understanding of {role.lower()} principles.",
            "1+ project or work sample demonstrating relevant skills.",
            "Comfort working in a team and communicating progress clearly.",
        ],
        "learning_path": [
            {
                "step": 1,
                "title": "Learn the fundamentals",
                "duration": "1-2 months",
                "description": (
                    "Pick one structured course and finish it end-to-end. "
                    "Take notes and build the example projects alongside."
                ),
                "resources": [
                    "Coursera or edX intro course",
                    "freeCodeCamp",
                    "YouTube: any well-rated beginner playlist",
                ],
            },
            {
                "step": 2,
                "title": "Build a portfolio project",
                "duration": "1 month",
                "description": (
                    "Ship one real, useful project. Put the code on GitHub with "
                    "a clean README and a short demo video or screenshots."
                ),
                "resources": ["GitHub", "Personal blog or Notion site"],
            },
            {
                "step": 3,
                "title": "Practice interviews",
                "duration": "3-4 weeks",
                "description": (
                    "Mock interviews with peers, solve domain-specific problems, "
                    "and rehearse stories using the STAR format."
                ),
                "resources": ["Pramp", "Glassdoor interview questions", "LinkedIn"],
            },
            {
                "step": 4,
                "title": "Apply, iterate, and network",
                "duration": "Ongoing",
                "description": (
                    "Apply to roles weekly, ask for feedback, and improve your "
                    "resume + portfolio based on what you learn."
                ),
                "resources": ["LinkedIn Jobs", "AngelList", "Local meetups"],
            },
        ],
        "estimated_time": "4-8 months for an entry-level offer",
        "career_growth": [
            f"Senior {role}",
            f"Lead {role}",
            "Specialist / Architect tracks",
        ],
        "source": "fallback",
        "_note": reason or None,
    }
