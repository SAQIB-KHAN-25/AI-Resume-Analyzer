def calculate_match_score(resume_skills, jd_skills):
    """
    Calculate match score between resume skills and job description skills.

    Args:
        resume_skills: List of skills from resume
        jd_skills: List of skills from job description

    Returns:
        Dictionary containing:
        - match_score: Percentage score (0-100)
        - matched_skills: List of matched skills
        - missing_skills: List of missing skills
    """
    # Convert to lowercase sets for case-insensitive comparison
    resume_set = set([s.lower().strip() for s in resume_skills if s])
    jd_set = set([s.lower().strip() for s in jd_skills if s])

    # Calculate matched skills
    matched = resume_set.intersection(jd_set)

    # Calculate match score
    score = (len(matched) / len(jd_set)) * 100 if jd_set else 0

    # Calculate missing skills
    missing = jd_set - resume_set

    return {
        "match_score": round(score, 2),
        "matched_skills": sorted(list(matched)),
        "missing_skills": sorted(list(missing)),
        "total_jd_skills": len(jd_set),
        "matched_count": len(matched)
    }


def match_resume(resume_data, jd_data):
    """
    Legacy function for backward compatibility.
    Match resume data with job description data.
    """
    resume_skills = resume_data.get("skills", [])
    jd_skills = jd_data.get("skills", [])

    return calculate_match_score(resume_skills, jd_skills)
