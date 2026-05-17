import pdfplumber
from docx import Document
import re
import os
import json
from typing import Dict, Any, List, Optional
import logging
from .skill_extractor import extract_resume_skills

logger = logging.getLogger(__name__)

# Optional word-segmentation fallback for PDFs whose text layer
# concatenates words without spaces (common in some resume templates).
try:
    import wordninja  # type: ignore
    _WORDNINJA_AVAILABLE = True
except Exception:
    _WORDNINJA_AVAILABLE = False


def _split_glued_token(token: str) -> str:
    """
    Split a long, space-less token like 'Developedaprogramtodetectthehandsign'
    into 'Developed a program to detect the hand sign' using wordninja.
    Preserves punctuation and original casing where possible.
    """
    if not _WORDNINJA_AVAILABLE or not token:
        return token
    # Skip tokens that already contain spaces or are short enough
    if len(token) < 18:
        return token
    # Skip tokens that look like URLs/emails/code identifiers
    if any(ch in token for ch in ("@", "/", "\\", "://", ".com", ".io", "_")):
        return token

    # Separate trailing/leading punctuation
    m = re.match(r"^([\W_]*)(.+?)([\W_]*)$", token, flags=re.UNICODE)
    if not m:
        return token
    pre, core, post = m.group(1), m.group(2), m.group(3)

    # Don't segment numeric-heavy or all-caps acronyms
    if not re.search(r"[a-z]", core) or sum(c.isdigit() for c in core) > len(core) // 2:
        return token

    parts = wordninja.split(core)
    if len(parts) <= 1:
        return token
    # Reject if segmentation produced tons of single letters (probably an acronym/jumble)
    short_pieces = [p for p in parts if len(p) <= 1]
    if len(short_pieces) > len(parts) // 2:
        return token

    # Re-capitalize first segment if the original started uppercase
    if core[0:1].isupper() and parts:
        parts[0] = parts[0].capitalize()
    return pre + " ".join(parts) + post


def _desegment_text(text: str) -> str:
    """Apply word splitting to suspiciously long tokens line-by-line."""
    if not _WORDNINJA_AVAILABLE or not text:
        return text
    out_lines = []
    for line in text.split("\n"):
        # Split on whitespace but keep it
        new_tokens = []
        for tok in re.split(r"(\s+)", line):
            if tok.strip() and len(tok) >= 18:
                new_tokens.append(_split_glued_token(tok))
            else:
                new_tokens.append(tok)
        out_lines.append("".join(new_tokens))
    return "\n".join(out_lines)

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


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text content from PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text as string
    """
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Try the standard extractor first
                page_text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""

                # Heuristic: if many "long" tokens lack spaces, the PDF's text layer
                # is missing space glyphs. Fall back to word-level extraction which
                # reconstructs spacing from glyph x-coordinates.
                tokens = re.findall(r"\S+", page_text)
                long_tokens = [t for t in tokens if len(t) > 25]
                missing_spaces = len(long_tokens) >= 2 or (
                    tokens and len(long_tokens) / max(len(tokens), 1) > 0.05
                )

                if missing_spaces or not page_text.strip():
                    try:
                        words = page.extract_words(
                            x_tolerance=2,
                            y_tolerance=3,
                            keep_blank_chars=False,
                            use_text_flow=True,
                        )
                        if words:
                            # Group words by their line (top coordinate, rounded)
                            lines_map = {}
                            for w in words:
                                key = round(float(w.get("top", 0)) / 3.0)
                                lines_map.setdefault(key, []).append(w)
                            ordered_keys = sorted(lines_map.keys())
                            rebuilt_lines = []
                            for k in ordered_keys:
                                row = sorted(lines_map[k], key=lambda x: float(x.get("x0", 0)))
                                rebuilt_lines.append(" ".join(w["text"] for w in row))
                            page_text = "\n".join(rebuilt_lines)
                    except Exception:
                        pass

                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        logger.exception("Error extracting PDF")

    # Final cleanup: split any remaining glued-together tokens via dictionary segmentation
    text = _desegment_text(text)
    return text


def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text content from DOCX file.
    
    Args:
        file_path: Path to DOCX file
        
    Returns:
        Extracted text as string
    """
    text = ""
    try:
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        logger.exception("Error extracting DOCX")
    
    return text


def _ai_parse_resume(text: str) -> Optional[Dict[str, Any]]:
    """
    Use OpenAI to parse resume with high accuracy.
    
    Args:
        text: Raw resume text
        
    Returns:
        Parsed resume data or None if AI unavailable
    """
    if not _OPENAI_AVAILABLE or not _openai_client:
        return None
    
    try:
        # Generous text budget so long resumes (2-3 pages) are fully visible to
        # the model. 16k chars ≈ ~4k tokens, well within the 128k context of
        # gpt-4o-mini while leaving room for the response.
        truncated_text = text[:16000]
        if len(text) > 16000:
            logger.warning(
                "Resume text truncated from %d to 16000 chars before AI parsing",
                len(text),
            )

        prompt = f"""Parse this resume and extract structured information. Return ONLY valid JSON.

CRITICAL: Extract EVERY project, EVERY work experience, EVERY certification,
and EVERY achievement the resume lists. Do not summarize, skip, or cap at any
number — if the resume has 12 projects, the JSON must contain 12 projects.

RESUME TEXT:
{truncated_text}

Extract and return in this exact JSON format (the examples below show the
SHAPE of each entry — the real arrays may contain many more items):
{{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "phone number",
    "linkedin": "linkedin URL if found",
    "github": "github URL if found",
    "summary": "Professional summary or objective (2-3 sentences)",
    "education": {{
        "degree": "Highest degree (e.g., B.Tech in Computer Science)",
        "institution": "University/College name",
        "year": "Graduation year",
        "gpa": "GPA if mentioned"
    }},
    "experience_years": "X years (numeric estimate)",
    "work_experience": [
        {{
            "title": "Job Title",
            "company": "Company Name",
            "duration": "Start - End",
            "highlights": ["Key achievement 1", "Key achievement 2"]
        }}
    ],
    "skills": {{
        "technical": ["Python", "JavaScript", "React", "etc"],
        "tools": ["Git", "Docker", "AWS", "etc"],
        "soft_skills": ["Leadership", "Communication", "etc"]
    }},
    "projects": [
        {{"name": "Project A", "description": "What it does", "technologies": ["Tech1", "Tech2"]}},
        {{"name": "Project B", "description": "What it does", "technologies": ["Tech3"]}}
    ],
    "certifications": ["Cert1", "Cert2"],
    "languages": ["English", "Hindi", "etc"],
    "achievements": ["Achievement 1", "Achievement 2"]
}}

Rules:
- Include ALL projects in the "projects" array — do not drop, merge, or cap.
- If a field is not present in the resume, use null or an empty array.
- Return ONLY valid JSON, no markdown, no commentary."""

        response = _openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You are an expert resume parser. Extract structured information accurately and completely. Never truncate lists. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        result_text = response.choices[0].message.content.strip()
        # Clean up potential markdown formatting (should be unnecessary with
        # response_format=json_object but kept as a defensive fallback).
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()

        parsed = json.loads(result_text)
        # Log how many projects the AI returned — invaluable for debugging when
        # a user reports "missing projects" on the dashboard.
        n_projects = len(parsed.get("projects") or []) if isinstance(parsed, dict) else 0
        logger.info("AI resume parse: %d projects extracted", n_projects)
        return parsed
    except Exception as e:
        logger.exception("AI resume parsing error")
        return None


def extract_name(text: str) -> str:
    """
    Extract name from resume text (simple heuristic - first line or first capitalized words).
    
    Args:
        text: Resume text
        
    Returns:
        Extracted name
    """
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if line and len(line) < 50:  # Names are usually short
            # Check if line contains mostly alphabetic characters
            if re.match(r'^[A-Za-z\s\.]+$', line):
                return line
    return "Unknown"


def extract_skills_section(text: str) -> List[str]:
    """
    Extract every item literally listed under a Skills/Technical Skills section.

    This complements the canonical skill extractor (which only matches against
    skills.json). Any token-like phrase a candidate writes — even niche tools
    or domain terms not in our skills list — is captured here.

    Strategy:
      1. Find a Skills heading.
      2. Read lines until the next major section heading.
      3. For each line, strip "Category:" prefixes (e.g., "Languages: Python, Java")
         and split on commas / semicolons / pipes / bullets.
      4. Filter obvious noise (very long sentences, pure numbers, stop phrases).
    """
    if not text:
        return []

    lines = text.splitlines()
    skill_headings = (
        "skills", "technical skills", "core skills", "key skills",
        "technical proficiencies", "skill set", "areas of expertise",
        "core competencies", "competencies",
    )
    end_headings = (
        "experience", "work experience", "professional experience",
        "education", "projects", "certifications", "achievements",
        "awards", "summary", "objective", "languages", "hobbies",
        "interests", "publications", "references", "contact", "profile",
    )

    in_section = False
    collected_lines: List[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        lowered = line.lower().strip(":").strip()

        if not in_section:
            if lowered in skill_headings:
                in_section = True
            continue

        # End of skills section
        if lowered in end_headings:
            break
        # Heuristic: short ALL-CAPS heading without digits = new section
        if len(line) < 30 and line.isupper() and len(line.split()) <= 3:
            if not any(ch.isdigit() for ch in line):
                break
        collected_lines.append(line)

    # Tokenize collected lines
    raw_tokens: List[str] = []
    for line in collected_lines:
        # Strip leading bullets
        cleaned = re.sub(r"^[\u2022\u25CB\-\*\u2023\u2043\u00B7]\s*", "", line).strip()
        # Drop "Category:" prefix
        if ":" in cleaned and cleaned.index(":") < 40:
            cleaned = cleaned.split(":", 1)[1].strip()
        # Split on common separators
        parts = re.split(r"[,;|/\u2022\u00B7]| {2,}|\t+", cleaned)
        for part in parts:
            tok = part.strip(" .\t-–—")
            if tok:
                raw_tokens.append(tok)

    # Filter noise + dedupe (case-insensitive)
    seen = set()
    out: List[str] = []
    for tok in raw_tokens:
        lower = tok.lower()
        if lower in seen:
            continue
        # Length filter: skills are typically 1-40 chars
        if len(tok) < 2 or len(tok) > 40:
            continue
        # Skip pure numbers / years
        if re.fullmatch(r"[\d\s.\-+]+", tok):
            continue
        # Skip sentences (lots of words AND no comma-list context already split)
        if len(tok.split()) > 5:
            continue
        # Skip lines that are clearly not skills
        if any(kw in lower for kw in ("years experience", "year experience", "month")):
            continue
        seen.add(lower)
        out.append(tok)

    return out


def _format_ai_education(edu: Any) -> str:
    """
    Convert the AI's education output into a readable single-line string.

    The AI may return:
      - a string (use as-is)
      - a dict with keys like degree/institution/year/gpa
      - a list of such dicts (multiple entries)
    Returns "" if nothing usable was found.
    """
    if not edu:
        return ""
    if isinstance(edu, str):
        return edu.strip()

    def _format_one(entry: Any) -> str:
        if isinstance(entry, str):
            return entry.strip()
        if not isinstance(entry, dict):
            return str(entry).strip()
        parts = []
        degree = (entry.get("degree") or "").strip()
        institution = (entry.get("institution") or entry.get("school") or
                       entry.get("university") or "").strip()
        year = str(entry.get("year") or entry.get("graduation_year") or "").strip()
        gpa = str(entry.get("gpa") or entry.get("cgpa") or "").strip()
        if degree:
            parts.append(degree)
        if institution:
            parts.append(institution)
        if year:
            parts.append(year)
        if gpa:
            parts.append(f"GPA {gpa}")
        return " — ".join(parts)

    if isinstance(edu, list):
        items = [s for s in (_format_one(e) for e in edu) if s]
        return " | ".join(items)

    if isinstance(edu, dict):
        return _format_one(edu)

    return str(edu).strip()


def extract_education(text: str) -> str:
    """
    Extract education information from resume.

    Strategy:
      1. Locate an "Education" section heading and return the lines underneath
         (up to the next major section heading) joined with " | ".
      2. If no section is found, fall back to word-boundary regex matching of
         common degree keywords so we don't match substrings inside unrelated
         words (e.g. "ms" in "teams", "ba" in "database").
    """
    if not text:
        return "Not specified"

    lines = [ln.strip() for ln in text.splitlines()]
    section_headings = (
        "experience", "work experience", "professional experience",
        "projects", "skills", "technical skills", "certifications",
        "achievements", "awards", "summary", "objective", "languages",
        "hobbies", "interests", "publications", "references", "contact",
        "profile",
    )

    edu_lines: List[str] = []
    in_section = False
    for raw in lines:
        line = raw.strip()
        if not line:
            if in_section and edu_lines:
                # Allow one blank line, but stop after a second blank
                edu_lines.append("")
            continue

        lowered = line.lower().strip(":").strip()

        # Detect education heading start
        if not in_section and lowered in ("education", "academic background",
                                           "academics", "educational qualifications",
                                           "qualifications"):
            in_section = True
            continue

        if in_section:
            # End of section: another major heading
            if lowered in section_headings:
                break
            # Heuristic: a single short uppercase word that looks like a heading
            if len(line) < 30 and line.isupper() and len(line.split()) <= 3:
                # Treat as new section unless it contains digits (like "BS 2024")
                if not any(ch.isdigit() for ch in line):
                    break
            edu_lines.append(line)

    # Clean trailing blanks and merge consecutive blanks
    edu_lines = [ln for ln in edu_lines if ln]
    if edu_lines:
        # Cap at first 5 meaningful lines
        return " | ".join(edu_lines[:5])

    # Fallback: word-boundary degree keyword search
    degree_patterns = [
        r"\bB\.?\s?Tech\b", r"\bM\.?\s?Tech\b", r"\bB\.?E\.?\b", r"\bM\.?E\.?\b",
        r"\bMBA\b", r"\bBCA\b", r"\bMCA\b", r"\bPh\.?D\.?\b",
        r"\bB\.?Sc\.?\b", r"\bM\.?Sc\.?\b", r"\bB\.?S\.?\b", r"\bM\.?S\.?\b",
        r"\bBachelor(?:'s)?\b", r"\bMaster(?:'s)?\b", r"\bDiploma\b",
        r"\bAssociate(?:'s)?\b",
    ]
    found = []
    for pattern in degree_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            found.append(match.group(0))
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for token in found:
        key = token.lower().replace(".", "").replace(" ", "")
        if key not in seen:
            seen.add(key)
            deduped.append(token)
    return ", ".join(deduped) if deduped else "Not specified"


def extract_experience(text: str) -> str:
    """
    Extract experience information from resume.
    
    Args:
        text: Resume text
        
    Returns:
        Experience details
    """
    # Look for patterns like "2 years", "3+ years", "5 yrs"
    experience_pattern = r'(\d+)\+?\s*(years?|yrs?)'
    matches = re.findall(experience_pattern, text.lower())
    
    if matches:
        # Return the highest number found
        max_exp = max([int(match[0]) for match in matches])
        return f"{max_exp} years"
    
    return "Not specified"


def extract_projects(text: str) -> list:
    """
    Extract project information from resume.

    Returns a list of dicts: {name, description, technologies}.
    The description is built by collecting non-bullet wrap lines that
    immediately follow the title until the next bullet or blank gap.
    """
    projects: list = []
    lines = text.split("\n")

    # Look for section headers
    project_section_found = False
    project_keywords = ["project", "projects", "academic projects", "personal projects"]

    def _flush(current):
        if not current:
            return
        name = current["name"].strip()
        if not name:
            return
        desc = " ".join(current["desc_lines"]).strip()
        # Heuristic tech extraction: anything in a "Tech: ..." or "Technologies: ..." line
        techs = []
        for ln in current["desc_lines"]:
            m = re.search(r"(?i)\b(?:tech(?:nologies)?(?:\s+used)?|stack|tools(?:\s+used)?)\s*[:\-]\s*(.+)", ln)
            if m:
                techs.extend([t.strip(" .,;") for t in re.split(r"[,/|]", m.group(1)) if t.strip(" .,;")])
        # Dedupe while preserving order
        seen = set()
        techs_unique = []
        for t in techs:
            k = t.lower()
            if k and k not in seen and len(t) <= 40:
                seen.add(k)
                techs_unique.append(t)
        projects.append({
            "name": name,
            "description": desc,
            "technologies": techs_unique,
        })

    # Labels that look like "Title:" but are actually sub-fields inside a project,
    # not the project name itself.
    META_LABELS = {
        "tools used", "tools", "technologies used", "technologies", "tech",
        "tech stack", "stack", "description", "role", "duration",
        "responsibilities", "outcome", "outcomes", "result", "results",
        "summary", "objective", "github", "link", "links", "demo",
    }
    PRIMARY_BULLETS = ('•', '-', '*', '►', '▪', '■')
    SUB_BULLETS = ('○', '◦', '·', '–', '—')

    # Date-range pattern signaling a project header line
    # e.g. "Feb 2025 - Apr 2025", "Oct 2024 – Dec 2024", "2024 - Present"
    MONTHS_RE = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*"
    DATE_RANGE_RE = re.compile(
        rf"(?i)(?:{MONTHS_RE}\s+\d{{4}}|\b\d{{4}}\b)\s*[-–—to]+\s*"
        rf"(?:{MONTHS_RE}\s+\d{{4}}|\b\d{{4}}\b|Present|Current|Ongoing)"
    )

    def _indent_of(raw: str) -> int:
        return len(raw) - len(raw.lstrip(' \t'))

    current = None
    primary_indent = None  # indentation level of project titles (sub-bullets are deeper)
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()

        # Check if we're in projects section
        if any(keyword in line_lower for keyword in project_keywords):
            project_section_found = True
            continue

        if not project_section_found:
            continue

        # Stop at next major section
        if any(section in line_lower for section in ["experience", "education", "skills", "certification", "achievements", "languages", "hobbies"]):
            _flush(current)
            current = None
            break

        stripped = line.strip()
        if not stripped:
            if current is not None:
                current["desc_lines"].append("")
            continue

        indent = _indent_of(line)
        is_primary_bullet = stripped.startswith(PRIMARY_BULLETS)
        is_sub_bullet = stripped.startswith(SUB_BULLETS)

        # Strip leading bullet chars to inspect the text content
        body = stripped.lstrip('•-*○◦·–—►▪■ \t').strip()
        body_lower = body.lower()

        # Detect the pre-colon label, if any
        pre_colon = body.split(':', 1)[0].strip().lower() if ':' in body[:60] else ""
        is_meta_line = pre_colon in META_LABELS

        # Date-range header (e.g. "Project Name   Feb 2025 - Apr 2025")
        date_match = DATE_RANGE_RE.search(body)

        # Decide if this line is a NEW project title:
        looks_like_title = False
        if is_meta_line:
            looks_like_title = False
        elif date_match and len(body) <= 200:
            # A line with a date range is almost always a project header
            looks_like_title = True
        elif is_primary_bullet:
            looks_like_title = True
        elif is_sub_bullet:
            looks_like_title = False  # sub-bullets are description lines
        elif primary_indent is not None and indent > primary_indent:
            looks_like_title = False  # deeper indent = continuation
        elif ':' in body[:60] and 5 <= len(body) <= 120:
            looks_like_title = True
        elif current is None and 5 <= len(body) <= 120 and len(body.split()) <= 12:
            # First non-empty line in section without a current project — treat as title
            looks_like_title = True

        if looks_like_title:
            _flush(current)
            if primary_indent is None:
                primary_indent = indent
            title = body
            desc_seed = []
            # If a date range is present, strip it off the title and remember the dates
            if date_match:
                title = (body[:date_match.start()] + body[date_match.end():]).strip(" -–—\t")
            # If title contains a colon, split off pre-colon as name
            if ':' in title:
                pre, _, post = title.partition(':')
                if pre.strip():
                    title = pre.strip()
                    if post.strip():
                        desc_seed.append(post.strip())
            current = {"name": title, "desc_lines": desc_seed}
        elif current is not None:
            # Continuation / sub-bullet line — append to current description
            if len(current["desc_lines"]) < 12:
                current["desc_lines"].append(body if body else stripped)

    _flush(current)

    if not projects:
        return [{"name": "Not specified", "description": "", "technologies": []}]
    return projects


def extract_languages(text: str) -> list:
    """
    Extract spoken languages from resume (NOT programming languages).
    
    Args:
        text: Resume text
        
    Returns:
        List of spoken languages
    """
    # Only spoken languages - programming languages are already in skills
    spoken_languages = ["English", "Hindi", "Spanish", "French", "German", "Chinese", 
                       "Japanese", "Korean", "Arabic", "Portuguese", "Russian", 
                       "Italian", "Telugu", "Tamil", "Kannada", "Malayalam", "Bengali", 
                       "Marathi", "Gujarati", "Punjabi", "Urdu", "Odia", "Assamese"]
    
    found_languages = []
    text_lower = text.lower()
    
    for lang in spoken_languages:
        if lang.lower() in text_lower:
            if lang not in found_languages:
                found_languages.append(lang)
    
    return found_languages if found_languages else []


def extract_hobbies(text: str) -> list:
    """
    Extract hobbies and interests from resume.
    
    Args:
        text: Resume text
        
    Returns:
        List of hobbies
    """
    hobbies = []
    lines = text.split("\n")
    
    hobby_section_found = False
    hobby_keywords = ["hobbies", "interests", "personal interests", "activities"]
    
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        
        # Check if we're in hobbies section
        if any(keyword in line_lower for keyword in hobby_keywords):
            hobby_section_found = True
            # Sometimes hobbies are on the same line
            hobby_text = line_lower.split(':')[-1].strip()
            if hobby_text and len(hobby_text) > 3:
                hobbies_on_line = [h.strip() for h in re.split(r'[,;]', hobby_text) if h.strip()]
                hobbies.extend(hobbies_on_line)
            continue
        
        # If in hobbies section, extract hobbies
        if hobby_section_found:
            # Stop at next section or end
            if any(section in line_lower for section in ["references", "declaration", "certification", "----", "___"]):
                break
            
            # Extract hobbies (often comma or bullet separated)
            if line.strip() and len(line.strip()) > 2:
                cleaned_line = line.strip().lstrip('•-*○ ').strip()
                if cleaned_line:
                    # Split by common separators
                    items = [h.strip() for h in re.split(r'[,;]', cleaned_line) if h.strip()]
                    hobbies.extend(items)
            
            if len(hobbies) >= 5:  # Limit to reasonable number
                break
    
    return hobbies[:5] if hobbies else ["Not specified"]


def extract_additional_info(text: str) -> dict:
    """
    Extract additional information like certifications, achievements, links.
    
    Args:
        text: Resume text
        
    Returns:
        Dictionary with additional info
    """
    additional = {
        "certifications": [],
        "achievements": [],
        "linkedin": "",
        "github": "",
        "email": "",
        "phone": ""
    }
    
    # Extract email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    if emails:
        additional["email"] = emails[0]
    
    # Extract phone
    phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
    phones = re.findall(phone_pattern, text)
    if phones:
        additional["phone"] = phones[0].strip()
    
    # Extract LinkedIn
    linkedin_pattern = r'linkedin\.com/in/[\w\-]+'
    linkedin = re.search(linkedin_pattern, text.lower())
    if linkedin:
        additional["linkedin"] = linkedin.group(0)
    
    # Extract GitHub
    github_pattern = r'github\.com/[\w\-]+'
    github = re.search(github_pattern, text.lower())
    if github:
        additional["github"] = github.group(0)
    
    # Extract certifications
    lines = text.split("\n")
    cert_section_found = False
    for line in lines:
        line_lower = line.lower().strip()
        if "certification" in line_lower or "certificate" in line_lower:
            cert_section_found = True
            continue
        if cert_section_found:
            if any(section in line_lower for section in ["experience", "education", "projects", "skills"]):
                break
            if line.strip() and len(line.strip()) > 5:
                cert = line.strip().lstrip('•-*○ ').strip()
                if cert and len(additional["certifications"]) < 3:
                    additional["certifications"].append(cert)
    
    return additional


def parse_resume(file_path: str, file_type: str, use_ai: bool = True) -> dict:
    """
    Parse resume and extract structured data.
    Uses OpenAI for enhanced parsing when available.
    
    Args:
        file_path: Path to resume file
        file_type: Type of file ('pdf' or 'docx')
        use_ai: Whether to use AI-enhanced parsing (default True)
        
    Returns:
        Dictionary containing extracted resume data
    """
    # Extract text based on file type
    if file_type == "pdf":
        text = extract_text_from_pdf(file_path)
    elif file_type == "docx":
        text = extract_text_from_docx(file_path)
    else:
        return {"error": "Unsupported file type"}
    
    if not text.strip():
        return {"error": "Could not extract text from file"}
    
    # Try AI-enhanced parsing first
    ai_result = None
    if use_ai and _OPENAI_AVAILABLE:
        ai_result = _ai_parse_resume(text)
    
    if ai_result:
        # Use AI results + fallback extractors so NO skill is dropped
        all_skills: List[str] = []
        seen_lower = set()

        def _add_skill(item: Any) -> None:
            if not isinstance(item, str):
                return
            cleaned = item.strip()
            if not cleaned:
                return
            key = cleaned.lower()
            if key in seen_lower:
                return
            seen_lower.add(key)
            all_skills.append(cleaned)

        # 1. AI-extracted skills (any category, any shape)
        skills_data = ai_result.get("skills")
        if isinstance(skills_data, dict):
            for value in skills_data.values():
                if isinstance(value, list):
                    for item in value:
                        _add_skill(item)
                else:
                    _add_skill(value)
        elif isinstance(skills_data, list):
            for item in skills_data:
                _add_skill(item)
        elif isinstance(skills_data, str):
            _add_skill(skills_data)

        # 2. Literal items from the resume's Skills section (catches niche skills)
        for item in extract_skills_section(text):
            _add_skill(item)

        # 3. Canonical skill extractor (catches skills mentioned outside the section)
        for item in extract_resume_skills(text):
            _add_skill(item)
        
        # Build work experience summary
        work_exp = ai_result.get("work_experience", [])
        work_summary = []
        if work_exp:
            for job in work_exp[:3]:
                if isinstance(job, dict):
                    title = job.get("title", "")
                    company = job.get("company", "")
                    if title and company:
                        work_summary.append(f"{title} at {company}")
        
        # Build projects list — keep description + technologies for UI popups.
        # No cap: surface every project the AI found so the UI can show them all.
        projects_list = []
        projects_data = ai_result.get("projects", [])
        for proj in projects_data:
            if isinstance(proj, dict):
                name = (proj.get("name") or "").strip()
                if not name:
                    continue
                projects_list.append({
                    "name": name,
                    "description": (proj.get("description") or "").strip(),
                    "technologies": [
                        str(t).strip() for t in (proj.get("technologies") or []) if str(t).strip()
                    ],
                })
            elif isinstance(proj, str) and proj.strip():
                projects_list.append({
                    "name": proj.strip(),
                    "description": "",
                    "technologies": [],
                })
        
        resume_data = {
            "name": ai_result.get("name") or extract_name(text),
            "skills": all_skills,
            "education": _format_ai_education(ai_result.get("education")) or extract_education(text),
            "experience": ai_result.get("experience_years") or extract_experience(text),
            "work_experience": work_summary,
            "projects": projects_list if projects_list else extract_projects(text),
            "languages": ai_result.get("languages", []) or extract_languages(text),
            "hobbies": extract_hobbies(text),
            "summary": ai_result.get("summary", ""),
            "certifications": ai_result.get("certifications", []),
            "achievements": ai_result.get("achievements", []),
            "additional_info": {
                "email": ai_result.get("email") or "",
                "phone": ai_result.get("phone") or "",
                "linkedin": ai_result.get("linkedin") or "",
                "github": ai_result.get("github") or "",
                "certifications": ai_result.get("certifications", [])
            },
            "raw_text": text,
            "ai_enhanced": True
        }
    else:
        # Fallback to traditional parsing
        name = extract_name(text)
        # Merge section-based + canonical so no skill is dropped
        section_skills = extract_skills_section(text)
        canonical_skills = extract_resume_skills(text)
        skills: List[str] = []
        seen_lower = set()
        for item in [*section_skills, *canonical_skills]:
            key = item.lower().strip()
            if not key or key in seen_lower:
                continue
            seen_lower.add(key)
            skills.append(item.strip())
        education = extract_education(text)
        experience = extract_experience(text)
        projects = extract_projects(text)
        languages = extract_languages(text)
        hobbies = extract_hobbies(text)
        additional_info = extract_additional_info(text)
        
        resume_data = {
            "name": name,
            "skills": skills,
            "education": education,
            "experience": experience,
            "work_experience": [],
            "projects": projects,
            "languages": languages,
            "hobbies": hobbies,
            "summary": "",
            "certifications": additional_info.get("certifications", []),
            "achievements": [],
            "additional_info": additional_info,
            "raw_text": text,
            "ai_enhanced": False
        }
    
    return resume_data
