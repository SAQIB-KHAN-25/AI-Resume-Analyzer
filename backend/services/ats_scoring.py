"""
ATS (Applicant Tracking System) Scoring Module
Week 5 Implementation - Professional Resume Evaluation

Scoring Weights:
- Keyword Matching: 45%
- Skill Matching: 25%
- Section Completeness: 15%
- Experience Matching: 15%

Additional Analysis:
- Resume length evaluation
- Formatting quality check
- Keyword density analysis
- Actionable recommendations
"""

from typing import Dict, List, Any, Set


# ============================================
# HELPER FUNCTIONS
# ============================================

def safe_divide(numerator: float, denominator: float, multiplier: float = 100) -> float:
    """Safely divide two numbers, returning 0 if denominator is 0."""
    return (numerator / denominator) * multiplier if denominator else 0


def normalize_set(items: List[str]) -> Set[str]:
    """Convert list to lowercase set for comparison."""
    return set(s.strip().lower() for s in items if s and isinstance(s, str))


# ============================================
# INDIVIDUAL SCORING FUNCTIONS
# ============================================

def calculate_keyword_score(resume_keywords: List[str], jd_keywords: List[str]) -> Dict[str, Any]:
    """
    Calculate keyword matching score (45% weight).
    Keywords are general terms extracted from text via NLP.
    """
    resume_set = normalize_set(resume_keywords)
    jd_set = normalize_set(jd_keywords)

    matched = resume_set & jd_set
    missing = jd_set - resume_set

    score = safe_divide(len(matched), len(jd_set))

    return {
        "score": round(score, 2),
        "matched": sorted(list(matched)),
        "missing": sorted(list(missing)),
        "total_required": len(jd_set),
        "matched_count": len(matched)
    }


def calculate_skill_score(resume_skills: List[str], jd_skills: List[str]) -> Dict[str, Any]:
    """
    Calculate skill matching score (25% weight).
    Skills are technical competencies from the skills database.
    """
    resume_set = normalize_set(resume_skills)
    jd_set = normalize_set(jd_skills)

    matched = resume_set & jd_set
    missing = jd_set - resume_set

    score = safe_divide(len(matched), len(jd_set))

    return {
        "score": round(score, 2),
        "matched": sorted(list(matched)),
        "missing": sorted(list(missing)),
        "total_required": len(jd_set),
        "matched_count": len(matched)
    }


def calculate_education_score(resume_education: List[str], required_education: List[str]) -> Dict[str, Any]:
    """
    Calculate education matching score.
    Returns 100 if no education requirement specified in JD.
    """
    resume_set = normalize_set(resume_education)
    jd_set = normalize_set(required_education)

    if not jd_set:
        return {
            "score": 100.0,
            "matched": list(resume_set),
            "missing": [],
            "note": "No specific education requirement"
        }

    matched = resume_set & jd_set
    missing = jd_set - resume_set

    score = safe_divide(len(matched), len(jd_set))

    return {
        "score": round(score, 2),
        "matched": sorted(list(matched)),
        "missing": sorted(list(missing))
    }


def calculate_experience_score(resume_exp_years: float, required_exp_years: float) -> Dict[str, Any]:
    """
    Calculate experience matching score.
    Returns 100 if no experience requirement or if resume meets/exceeds requirement.
    """
    if required_exp_years == 0:
        return {
            "score": 100.0,
            "resume_years": resume_exp_years,
            "required_years": required_exp_years,
            "note": "No experience requirement specified"
        }

    if resume_exp_years >= required_exp_years:
        return {
            "score": 100.0,
            "resume_years": resume_exp_years,
            "required_years": required_exp_years,
            "note": "Meets or exceeds requirement"
        }

    score = safe_divide(resume_exp_years, required_exp_years)
    gap = required_exp_years - resume_exp_years

    return {
        "score": round(score, 2),
        "resume_years": resume_exp_years,
        "required_years": required_exp_years,
        "gap_years": gap,
        "note": f"Missing {gap:.1f} years of experience"
    }


def calculate_section_structure_score(sections: List[str]) -> Dict[str, Any]:
    """
    Calculate section structure completeness score.
    Evaluates presence of required and optional resume sections.
    """
    sections_set = normalize_set(sections)

    # Required sections (70% of section score)
    REQUIRED_SECTIONS = {"education", "experience", "skills", "projects"}

    # Optional but valuable sections (30% of section score)
    OPTIONAL_SECTIONS = {"certifications", "achievements", "summary", "objective"}

    required_found = sections_set & REQUIRED_SECTIONS
    optional_found = sections_set & OPTIONAL_SECTIONS

    required_score = safe_divide(len(required_found), len(REQUIRED_SECTIONS)) * 0.7
    optional_score = safe_divide(len(optional_found), len(OPTIONAL_SECTIONS)) * 0.3

    total_score = required_score + optional_score

    missing_required = REQUIRED_SECTIONS - sections_set
    missing_optional = OPTIONAL_SECTIONS - sections_set

    return {
        "score": round(total_score, 2),
        "required_found": sorted(list(required_found)),
        "required_missing": sorted(list(missing_required)),
        "optional_found": sorted(list(optional_found)),
        "optional_missing": sorted(list(missing_optional))
    }


def calculate_combined_section_score(
    education_result: Dict[str, Any],
    structure_result: Dict[str, Any]
) -> float:
    """
    Combine education and structure scores into final section score.
    Education: 60%, Structure: 40%
    """
    education_score = education_result.get("score", 0)
    structure_score = structure_result.get("score", 0)

    combined = (0.6 * education_score) + (0.4 * structure_score)
    return round(combined, 2)


# ============================================
# ADDITIONAL ANALYSIS (BONUS FROM WEEK 5 SPEC)
# ============================================

def calculate_length_score(text: str) -> Dict[str, Any]:
    """
    Evaluate resume length (ideal: 300-800 words for 1-2 pages).
    """
    if not text:
        return {"score": 0, "word_count": 0, "status": "empty"}

    word_count = len(text.split())

    if word_count < 150:
        score = 30
        status = "too_short"
        suggestion = "Resume is too brief. Add more details about your experience and skills."
    elif word_count < 300:
        score = 60
        status = "short"
        suggestion = "Consider adding more detail to strengthen your resume."
    elif word_count <= 800:
        score = 100
        status = "ideal"
        suggestion = "Resume length is optimal."
    elif word_count <= 1200:
        score = 80
        status = "long"
        suggestion = "Resume is slightly long. Consider condensing less relevant information."
    else:
        score = 50
        status = "too_long"
        suggestion = "Resume is too long. Focus on most relevant experiences and skills."

    return {
        "score": score,
        "word_count": word_count,
        "status": status,
        "suggestion": suggestion
    }


def calculate_format_score(text: str) -> Dict[str, Any]:
    """
    Evaluate resume formatting quality.
    Checks for bullet points, clean structure, proper formatting.
    """
    if not text:
        return {"score": 0, "issues": ["Empty resume"]}

    score = 60  # Base score
    issues = []
    positives = []

    # Check for bullet points (good formatting)
    bullet_chars = ['•', '-', '▪', '○', '►', '*']
    has_bullets = any(char in text for char in bullet_chars)
    if has_bullets:
        score += 15
        positives.append("Uses bullet points for clarity")
    else:
        issues.append("Consider using bullet points for better readability")

    # Check for section headers (ALL CAPS or Title Case patterns)
    common_headers = ["EDUCATION", "EXPERIENCE", "SKILLS", "PROJECTS", "Education", "Experience", "Skills", "Projects"]
    headers_found = sum(1 for h in common_headers if h in text)
    if headers_found >= 3:
        score += 15
        positives.append("Clear section headers")
    elif headers_found >= 1:
        score += 5
        issues.append("Add clear section headers for all sections")
    else:
        issues.append("Missing section headers")

    # Check for excessive special characters (bad formatting)
    special_count = sum(1 for c in text if c in '~`@#$%^&=+[]{}|\\<>')
    if special_count > 20:
        score -= 10
        issues.append("Reduce use of special characters")
    else:
        positives.append("Clean character usage")

    # Check for contact info patterns (professionalism)
    has_email = '@' in text and '.' in text
    has_phone = any(c.isdigit() for c in text)
    if has_email and has_phone:
        score += 10
        positives.append("Contact information present")
    else:
        issues.append("Ensure contact information is clearly visible")

    score = max(0, min(100, score))

    return {
        "score": score,
        "positives": positives,
        "issues": issues
    }


def calculate_keyword_density(text: str, jd_skills: List[str]) -> Dict[str, Any]:
    """
    Analyze how frequently JD skills appear in resume.
    Higher density (with natural limits) indicates strong relevance.
    """
    if not text or not jd_skills:
        return {"score": 0, "density_map": {}}

    text_lower = text.lower()
    density_map = {}
    total_mentions = 0

    for skill in jd_skills:
        skill_lower = skill.lower().strip()
        if skill_lower:
            count = text_lower.count(skill_lower)
            if count > 0:
                density_map[skill] = count
                total_mentions += count

    # Score: each mention worth 5 points, capped at 100
    # This rewards natural repetition without over-stuffing
    score = min(total_mentions * 5, 100)

    skills_mentioned = len(density_map)

    return {
        "score": score,
        "total_mentions": total_mentions,
        "skills_mentioned": skills_mentioned,
        "density_map": density_map
    }


# ============================================
# RECOMMENDATIONS ENGINE
# ============================================

def generate_recommendations(
    keyword_result: Dict[str, Any],
    skill_result: Dict[str, Any],
    experience_result: Dict[str, Any],
    section_result: Dict[str, Any],
    length_result: Dict[str, Any],
    format_result: Dict[str, Any],
    final_score: float
) -> Dict[str, Any]:
    """
    Generate actionable recommendations based on scoring analysis.
    """
    critical = []  # Must fix
    important = []  # Should fix
    suggestions = []  # Nice to have
    strengths = []  # What's working well

    # Analyze keyword gaps
    if keyword_result["score"] < 50:
        critical.append({
            "area": "Keywords",
            "issue": "Low keyword match with job description",
            "action": f"Add these keywords to your resume: {', '.join(keyword_result['missing'][:5])}"
        })
    elif keyword_result["score"] < 75:
        important.append({
            "area": "Keywords",
            "issue": "Moderate keyword match",
            "action": f"Consider adding: {', '.join(keyword_result['missing'][:3])}"
        })
    else:
        strengths.append("Strong keyword alignment with job description")

    # Analyze skill gaps
    if skill_result["score"] < 50:
        critical.append({
            "area": "Skills",
            "issue": "Missing critical technical skills",
            "action": f"Highlight or acquire these skills: {', '.join(skill_result['missing'][:5])}"
        })
    elif skill_result["score"] < 75:
        important.append({
            "area": "Skills",
            "issue": "Some required skills missing",
            "action": f"Add if you have them: {', '.join(skill_result['missing'][:3])}"
        })
    else:
        strengths.append("Technical skills well-matched to requirements")

    # Analyze experience
    if experience_result["score"] < 100 and experience_result.get("gap_years"):
        gap = experience_result["gap_years"]
        if gap > 2:
            important.append({
                "area": "Experience",
                "issue": f"Missing {gap:.1f} years of required experience",
                "action": "Highlight transferable experience, projects, or relevant coursework"
            })
        else:
            suggestions.append({
                "area": "Experience",
                "issue": f"Slightly below experience requirement ({gap:.1f} years)",
                "action": "Emphasize quality of experience over quantity"
            })
    elif experience_result["score"] == 100:
        strengths.append("Experience level meets requirements")

    # Analyze sections
    if section_result.get("required_missing"):
        missing = section_result["required_missing"]
        important.append({
            "area": "Resume Structure",
            "issue": f"Missing sections: {', '.join(missing)}",
            "action": "Add these essential sections to your resume"
        })
    else:
        strengths.append("All essential sections present")

    # Length feedback
    if length_result["status"] in ["too_short", "too_long"]:
        important.append({
            "area": "Resume Length",
            "issue": length_result["suggestion"],
            "action": "Aim for 300-800 words (1-2 pages)"
        })

    # Format feedback
    if format_result.get("issues"):
        for issue in format_result["issues"][:2]:
            suggestions.append({
                "area": "Formatting",
                "issue": issue,
                "action": "Improve resume readability"
            })

    # Overall assessment
    if final_score >= 80:
        overall = "Excellent match! Your resume is well-aligned with this position."
    elif final_score >= 65:
        overall = "Good match with room for improvement. Focus on critical areas."
    elif final_score >= 50:
        overall = "Moderate match. Address the recommendations to improve your chances."
    else:
        overall = "Low match. Consider if this role aligns with your experience, or significantly revise your resume."

    return {
        "overall_assessment": overall,
        "strengths": strengths,
        "critical_improvements": critical,
        "important_improvements": important,
        "suggestions": suggestions,
        "improvement_potential": round(100 - final_score, 2)
    }


# ============================================
# MAIN ATS SCORING FUNCTION
# ============================================

def calculate_ats_score(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate comprehensive ATS score with detailed breakdown.

    Required Input Fields:
    - resume_keywords: List[str] - Keywords extracted from resume
    - jd_keywords: List[str] - Keywords from job description
    - resume_skills: List[str] - Skills extracted from resume
    - jd_skills: List[str] - Skills from job description
    - sections: List[str] - Resume sections detected (e.g., ["education", "experience", "skills"])
    - resume_education: List[str] - Education qualifications from resume
    - required_education: List[str] - Required education from JD (optional)
    - experience_years: float - Years of experience from resume
    - required_experience: float - Required years from JD (optional)
    - resume_text: str - Full resume text (for additional analysis)

    Returns:
    - ats_score: Final weighted score (0-100)
    - breakdown: Individual component scores
    - details: Matched/missing items for each category
    - analysis: Additional metrics (length, format, density)
    - recommendations: Actionable improvement suggestions
    """

    # Extract inputs with safe defaults
    resume_keywords = data.get("resume_keywords", [])
    jd_keywords = data.get("jd_keywords", [])
    resume_skills = data.get("resume_skills", [])
    jd_skills = data.get("jd_skills", [])
    sections = data.get("sections", [])
    resume_education = data.get("resume_education", [])
    required_education = data.get("required_education", [])
    experience_years = float(data.get("experience_years", 0))
    required_experience = float(data.get("required_experience", 0))
    resume_text = data.get("resume_text", "")

    # Calculate individual scores
    keyword_result = calculate_keyword_score(resume_keywords, jd_keywords)
    skill_result = calculate_skill_score(resume_skills, jd_skills)
    education_result = calculate_education_score(resume_education, required_education)
    experience_result = calculate_experience_score(experience_years, required_experience)
    structure_result = calculate_section_structure_score(sections)

    # Combined section score (education + structure)
    section_score = calculate_combined_section_score(education_result, structure_result)

    # Additional analysis
    length_result = calculate_length_score(resume_text)
    format_result = calculate_format_score(resume_text)
    density_result = calculate_keyword_density(resume_text, jd_skills)

    # Calculate final weighted ATS score
    # Weights: Keywords 45%, Skills 25%, Sections 15%, Experience 15%
    final_score = (
        0.45 * keyword_result["score"] +
        0.25 * skill_result["score"] +
        0.15 * section_score +
        0.15 * experience_result["score"]
    )

    # Clamp score between 0-100
    final_score = max(0, min(100, final_score))
    final_score = round(final_score, 2)

    # Generate recommendations
    recommendations = generate_recommendations(
        keyword_result=keyword_result,
        skill_result=skill_result,
        experience_result=experience_result,
        section_result=structure_result,
        length_result=length_result,
        format_result=format_result,
        final_score=final_score
    )

    # Determine score category
    if final_score >= 80:
        score_category = "excellent"
        score_label = "Excellent Match"
    elif final_score >= 65:
        score_category = "good"
        score_label = "Good Match"
    elif final_score >= 50:
        score_category = "moderate"
        score_label = "Moderate Match"
    else:
        score_category = "low"
        score_label = "Needs Improvement"

    return {
        "ats_score": final_score,
        "score_category": score_category,
        "score_label": score_label,

        "breakdown": {
            "keyword_score": keyword_result["score"],
            "skill_score": skill_result["score"],
            "section_score": section_score,
            "experience_score": experience_result["score"],
            "education_score": education_result["score"],
            "structure_score": structure_result["score"]
        },

        "weights": {
            "keyword": "45%",
            "skill": "25%",
            "section": "15%",
            "experience": "15%"
        },

        "details": {
            "keywords": {
                "matched": keyword_result["matched"],
                "missing": keyword_result["missing"],
                "match_rate": f"{keyword_result['matched_count']}/{keyword_result['total_required']}"
            },
            "skills": {
                "matched": skill_result["matched"],
                "missing": skill_result["missing"],
                "match_rate": f"{skill_result['matched_count']}/{skill_result['total_required']}"
            },
            "education": {
                "matched": education_result.get("matched", []),
                "missing": education_result.get("missing", []),
                "note": education_result.get("note", "")
            },
            "experience": {
                "resume_years": experience_result["resume_years"],
                "required_years": experience_result["required_years"],
                "note": experience_result.get("note", "")
            },
            "sections": {
                "present": structure_result["required_found"] + structure_result["optional_found"],
                "missing_required": structure_result["required_missing"],
                "missing_optional": structure_result["optional_missing"]
            }
        },

        "analysis": {
            "length": length_result,
            "format": format_result,
            "keyword_density": density_result
        },

        "recommendations": recommendations
    }


# ============================================
# LEGACY SUPPORT
# ============================================

def calculate_ats(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    Simple scoring based on skills count only.
    """
    skills_count = len(resume_data.get("skills", []))
    score = min(skills_count * 10, 100)

    return {
        "ats_score": score,
        "note": "Legacy scoring - use calculate_ats_score for full analysis"
    }
