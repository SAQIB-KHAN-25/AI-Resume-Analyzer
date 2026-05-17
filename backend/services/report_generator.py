"""
Report Generator Service
Generates PDF and text reports for resume analysis results.
"""
import os
from datetime import datetime
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'reports')


def ensure_reports_directory():
    """Ensure reports directory exists."""
    os.makedirs(REPORTS_DIR, exist_ok=True)


def generate_text_report(
    resume_data: Dict[str, Any],
    jd_data: Optional[Dict[str, Any]] = None,
    match_result: Optional[Dict[str, Any]] = None,
    ats_result: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a text report for resume analysis.
    
    Args:
        resume_data: Parsed resume data
        jd_data: Job description data (optional)
        match_result: Match analysis result (optional)
        ats_result: ATS score result (optional)
        
    Returns:
        Path to generated report file
    """
    ensure_reports_directory()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resume_analysis_{timestamp}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("         AI RESUME ANALYZER - ANALYSIS REPORT\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Resume Summary
        f.write("-" * 40 + "\n")
        f.write("RESUME SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Name: {resume_data.get('name', 'Not found')}\n")
        f.write(f"Education: {resume_data.get('education', 'Not specified')}\n")
        f.write(f"Experience: {resume_data.get('experience', 'Not specified')}\n\n")

        skills = resume_data.get('skills', [])
        if skills:
            f.write(f"Skills ({len(skills)}):\n")
            for skill in skills[:20]:
                f.write(f"  • {skill}\n")
            if len(skills) > 20:
                f.write(f"  ... and {len(skills) - 20} more\n")
        f.write("\n")

        # Match Results
        if match_result:
            f.write("-" * 40 + "\n")
            f.write("MATCH ANALYSIS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Match Score: {match_result.get('match_score', 0):.2f}%\n")
            f.write(f"Matched Skills: {match_result.get('matched_count', 0)}/{match_result.get('total_jd_skills', 0)}\n\n")

            matched = match_result.get('matched_skills', [])
            if matched:
                f.write("Matched Skills:\n")
                for skill in matched:
                    f.write(f"  ✓ {skill}\n")

            missing = match_result.get('missing_skills', [])
            if missing:
                f.write("\nMissing Skills:\n")
                for skill in missing:
                    f.write(f"  ✗ {skill}\n")
            f.write("\n")

        # ATS Score
        if ats_result:
            f.write("-" * 40 + "\n")
            f.write("ATS SCORE ANALYSIS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Overall ATS Score: {ats_result.get('ats_score', 0)}%\n")
            f.write(f"Rating: {ats_result.get('score_label', 'N/A')}\n\n")

            breakdown = ats_result.get('breakdown', {})
            if breakdown:
                f.write("Score Breakdown:\n")
                f.write(f"  Keywords:   {breakdown.get('keyword_score', 0)}%\n")
                f.write(f"  Skills:     {breakdown.get('skill_score', 0)}%\n")
                f.write(f"  Sections:   {breakdown.get('section_score', 0)}%\n")
                f.write(f"  Experience: {breakdown.get('experience_score', 0)}%\n")
            f.write("\n")

        f.write("=" * 60 + "\n")
        f.write("End of Report\n")
        f.write("=" * 60 + "\n")
    
    return filepath


def generate_summary_report(data: Dict[str, Any]) -> str:
    """
    Generate a simple summary report.
    
    Args:
        data: Any analysis data
        
    Returns:
        Path to generated report file
    """
    ensure_reports_directory()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"summary_{timestamp}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("Analysis Summary Report\n")
        f.write("=" * 40 + "\n\n")
        f.write(str(data))
    
    return filepath


def _draw_wrapped_text(c: canvas.Canvas, text: str, x: float, y: float, max_width: float, line_height: float = 14) -> float:
    """Draw wrapped text and return the new y position."""
    words = text.split()
    if not words:
        return y - line_height

    current_line = words[0]
    for word in words[1:]:
        trial = f"{current_line} {word}"
        if c.stringWidth(trial, "Helvetica", 11) <= max_width:
            current_line = trial
        else:
            c.drawString(x, y, current_line)
            y -= line_height
            current_line = word
    c.drawString(x, y, current_line)
    return y - line_height


def _new_page_if_needed(c: canvas.Canvas, y: float, threshold: float = 70) -> float:
    if y > threshold:
        return y
    c.showPage()
    c.setFont("Helvetica", 11)
    return 760


def generate_pdf_report(data: Dict[str, Any], filename: Optional[str] = None) -> str:
    """Generate a PDF report with match, ATS, role, and recommendation insights."""
    ensure_reports_directory()

    if not filename:
        filename = f"resume_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    filepath = os.path.join(REPORTS_DIR, filename)
    c = canvas.Canvas(filepath, pagesize=letter)
    width, _ = letter

    y = 760
    margin_x = 72
    usable_width = width - (2 * margin_x)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin_x, y, "AI Resume Analyzer - Report")
    y -= 24

    c.setFont("Helvetica", 10)
    c.drawString(margin_x, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 24

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Summary Scores")
    y -= 18

    c.setFont("Helvetica", 11)
    c.drawString(margin_x, y, f"Match Score: {data.get('match_score', 0)}%")
    y -= 16
    c.drawString(margin_x, y, f"ATS Score: {data.get('ats_score', 0)}%")
    y -= 20

    y = _new_page_if_needed(c, y)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Missing Skills")
    y -= 18

    c.setFont("Helvetica", 11)
    missing_skills = data.get("missing_skills", []) or []
    if missing_skills:
        for skill in missing_skills:
            y = _new_page_if_needed(c, y)
            c.drawString(margin_x + 14, y, f"- {skill}")
            y -= 14
    else:
        c.drawString(margin_x + 14, y, "- None")
        y -= 16

    y -= 8
    y = _new_page_if_needed(c, y)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Predicted Roles")
    y -= 18

    c.setFont("Helvetica", 11)
    predicted_roles = data.get("predicted_roles", []) or []
    if predicted_roles:
        for role in predicted_roles:
            y = _new_page_if_needed(c, y)
            role_name = role.get("role", "Unknown Role")
            role_score = role.get("score", 0)
            c.drawString(margin_x + 14, y, f"- {role_name} ({role_score}%)")
            y -= 14
    else:
        c.drawString(margin_x + 14, y, "- No role predictions available")
        y -= 16

    y -= 8
    y = _new_page_if_needed(c, y)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Recommendations")
    y -= 18

    c.setFont("Helvetica", 11)
    recommendations = data.get("recommendations", []) or []
    if recommendations:
        for recommendation in recommendations:
            y = _new_page_if_needed(c, y)
            y = _draw_wrapped_text(c, f"- {recommendation}", margin_x + 14, y, usable_width - 14)
    else:
        c.drawString(margin_x + 14, y, "- No recommendations generated")

    c.save()
    return filepath
