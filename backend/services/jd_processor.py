import re
import os
import json
from collections import Counter
from typing import Dict, List, Optional
import logging

from .skill_extractor import extract_jd_skills as extract_jd_skills_from_engine

logger = logging.getLogger(__name__)

try:
    import spacy
except Exception:  # pragma: no cover - optional dependency
    spacy = None

# OpenAI integration (optional enhancement)
try:
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv()
    _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    _OPENAI_AVAILABLE = bool(os.getenv("OPENAI_API_KEY"))
except Exception:
    _openai_client = None
    _OPENAI_AVAILABLE = False


FALLBACK_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "you", "your", "our",
    "will", "have", "has", "not", "but", "all", "any", "can", "job", "role", "work",
    "team", "years", "year", "experience", "required", "preferred", "must", "should",
    "who", "what", "when", "where", "why", "their", "they", "them", "its", "able",
    "skills", "skill", "candidate", "candidates", "responsibilities", "requirements"
}

_NLP = None
if spacy is not None:
    try:
        _NLP = spacy.load("en_core_web_sm")
    except Exception:
        _NLP = None


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _ai_parse_job_description(text: str) -> Optional[Dict]:
    """
    Use OpenAI to parse job description with high accuracy.
    
    Args:
        text: Raw JD text
        
    Returns:
        Parsed JD data or None if AI unavailable
    """
    if not _OPENAI_AVAILABLE or not _openai_client:
        return None
    
    try:
        prompt = f"""Parse this job description and extract structured information. Return ONLY valid JSON.

JOB DESCRIPTION:
{text[:4000]}

Extract and return in this exact JSON format:
{{
    "job_title": "The job title/position",
    "company": "Company name if mentioned",
    "location": "Location if mentioned",
    "job_type": "Full-time/Part-time/Contract/Remote",
    "experience_required": "X years or range",
    "education_required": "Degree requirements",
    "salary_range": "Salary if mentioned",
    "required_skills": {{
        "technical": ["Python", "JavaScript", "AWS", "etc - must have skills"],
        "tools": ["Git", "Docker", "JIRA", "etc"],
        "soft_skills": ["Communication", "Leadership", "etc"]
    }},
    "preferred_skills": ["Nice to have skills"],
    "responsibilities": ["Key responsibility 1", "Key responsibility 2"],
    "qualifications": ["Qualification 1", "Qualification 2"],
    "benefits": ["Benefit 1", "Benefit 2"],
    "keywords": ["important", "industry", "terms", "mentioned"],
    "role_level": "Entry/Junior/Mid/Senior/Lead/Manager",
    "team_size": "If mentioned",
    "industry": "Tech/Finance/Healthcare/etc"
}}

If any field is not found, use null or empty array. Return ONLY valid JSON, no markdown."""

        response = _openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You are an expert job description parser and HR analyst. Extract structured information accurately. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.2
        )
        
        result_text = response.choices[0].message.content.strip()
        # Clean up potential markdown formatting
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        return json.loads(result_text)
    except Exception as e:
        logger.exception("AI JD parsing error")
        return None


def extract_jd_skills(text: str) -> List[str]:
    """Extract required skills using the centralized Week-3 skill engine."""
    return extract_jd_skills_from_engine(text)


def _extract_keywords_with_spacy(text: str) -> List[str]:
    doc = _NLP(text)
    lemmas = []
    for token in doc:
        if token.is_stop or token.is_punct or token.like_num:
            continue
        if token.pos_ not in {"NOUN", "PROPN", "ADJ"}:
            continue

        lemma = token.lemma_.lower().strip()
        if len(lemma) < 3 or not re.search(r"[a-z]", lemma):
            continue
        lemmas.append(lemma)

    counts = Counter(lemmas)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _ in ordered]


def _extract_keywords_fallback(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text.lower())
    cleaned_tokens = [tok.strip("._-+") for tok in tokens]
    filtered = [tok for tok in cleaned_tokens if tok and tok not in FALLBACK_STOPWORDS]
    counts = Counter(filtered)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _ in ordered]


def extract_keywords(text: str, limit: int = 25) -> List[str]:
    """Extract meaningful keywords using spaCy when available, with safe fallback."""
    normalized = _normalize_text(text)
    if not normalized:
        return []

    if _NLP is not None:
        keywords = _extract_keywords_with_spacy(normalized)
    else:
        keywords = _extract_keywords_fallback(normalized)

    return keywords[:limit]


def _calculate_skill_coverage(required_skills: List[str], baseline_skills: int = 12) -> float:
    if baseline_skills <= 0:
        return 0.0
    coverage = (len(required_skills) / baseline_skills) * 100
    return round(min(100.0, coverage), 1)


def _calculate_top_keyword_density(text: str, keywords: List[str], top_n: int = 5) -> float:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", text.lower())
    if not tokens:
        return 0.0

    top_keywords = [kw.lower() for kw in keywords[:top_n]]
    if not top_keywords:
        return 0.0

    token_counts = Counter(tokens)
    top_hits = sum(token_counts.get(keyword, 0) for keyword in top_keywords)
    density = (top_hits / len(tokens)) * 100
    return round(density, 2)


def _infer_role_hints(required_skills: List[str], keywords: List[str], text: str) -> List[str]:
    signal_terms = {item.lower() for item in required_skills + keywords}
    signal_terms.update(re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text.lower()))

    role_map = {
        "Backend Engineer": {"python", "java", "node.js", "fastapi", "django", "flask", "rest", "api", "sql", "microservices"},
        "Frontend Engineer": {"react", "angular", "vue", "javascript", "typescript", "html", "css", "tailwind", "bootstrap"},
        "Full Stack Engineer": {"react", "node.js", "javascript", "typescript", "sql", "mongodb", "api"},
        "Data Scientist": {"python", "pandas", "numpy", "scikit-learn", "machine", "learning", "tensorflow", "pytorch", "statistics"},
        "ML Engineer": {"machine", "learning", "tensorflow", "pytorch", "mlops", "docker", "kubernetes", "python"},
        "DevOps Engineer": {"docker", "kubernetes", "aws", "azure", "gcp", "terraform", "jenkins", "ci/cd", "linux"},
        "Data Engineer": {"spark", "hadoop", "etl", "sql", "airflow", "data", "pipeline", "warehouse"},
        "QA Engineer": {"selenium", "pytest", "junit", "cypress", "postman", "testing", "automation"}
    }

    hints = []
    for role, terms in role_map.items():
        matched = len(signal_terms.intersection(terms))
        if matched >= 3:
            hints.append(role)

    return hints[:3]


def build_scoring_block(jd_text: str, required_skills: List[str], keywords: List[str]) -> Dict[str, object]:
    return {
        "skill_coverage_pct": _calculate_skill_coverage(required_skills),
        "top_keyword_density_pct": _calculate_top_keyword_density(jd_text, keywords),
        "role_hints": _infer_role_hints(required_skills, keywords, jd_text)
    }


def process_job_description(jd_text: str, use_ai: bool = True) -> Dict[str, object]:
    """
    Process job description text and return structured extraction results.
    Uses OpenAI for enhanced parsing when available.
    
    Args:
        jd_text: Raw job description text
        use_ai: Whether to use AI-enhanced parsing (default True)
        
    Returns:
        Dictionary with extracted JD data
    """
    normalized = _normalize_text(jd_text)
    if not normalized:
        return {
            "required_skills": [],
            "keywords": [],
            "text_preview": "",
            "scoring": {
                "skill_coverage_pct": 0.0,
                "top_keyword_density_pct": 0.0,
                "role_hints": []
            }
        }
    
    # Try AI-enhanced parsing first
    ai_result = None
    if use_ai and _OPENAI_AVAILABLE:
        ai_result = _ai_parse_job_description(normalized)
    
    if ai_result:
        # Combine AI-extracted skills with rule-based extraction
        all_skills = []
        if ai_result.get("required_skills"):
            skills_data = ai_result["required_skills"]
            if isinstance(skills_data, dict):
                all_skills.extend(skills_data.get("technical", []))
                all_skills.extend(skills_data.get("tools", []))
            elif isinstance(skills_data, list):
                all_skills.extend(skills_data)
        
        # Also extract with rule-based engine
        rule_skills = extract_jd_skills(normalized)
        for skill in rule_skills:
            if skill not in all_skills:
                all_skills.append(skill)
        
        # Get keywords from AI or extract
        keywords = ai_result.get("keywords", []) or extract_keywords(normalized)
        
        scoring = build_scoring_block(normalized, all_skills, keywords)
        
        # Add AI-detected role hints if available
        if ai_result.get("job_title"):
            if ai_result["job_title"] not in scoring["role_hints"]:
                scoring["role_hints"].insert(0, ai_result["job_title"])
        
        return {
            "job_title": ai_result.get("job_title"),
            "company": ai_result.get("company"),
            "location": ai_result.get("location"),
            "job_type": ai_result.get("job_type"),
            "experience_required": ai_result.get("experience_required"),
            "education_required": ai_result.get("education_required"),
            "role_level": ai_result.get("role_level"),
            "required_skills": all_skills,
            "preferred_skills": ai_result.get("preferred_skills", []),
            "responsibilities": ai_result.get("responsibilities", []),
            "qualifications": ai_result.get("qualifications", []),
            "benefits": ai_result.get("benefits", []),
            "keywords": keywords,
            "text_preview": normalized[:300],
            "scoring": scoring,
            "ai_enhanced": True
        }
    else:
        # Fallback to traditional parsing
        required_skills = extract_jd_skills(normalized)
        keywords = extract_keywords(normalized)
        scoring = build_scoring_block(normalized, required_skills, keywords)

        return {
            "job_title": None,
            "company": None,
            "location": None,
            "job_type": None,
            "experience_required": None,
            "education_required": None,
            "role_level": None,
            "required_skills": required_skills,
            "preferred_skills": [],
            "responsibilities": [],
            "qualifications": [],
            "benefits": [],
            "keywords": keywords,
            "text_preview": normalized[:300],
            "scoring": scoring,
            "ai_enhanced": False
        }
