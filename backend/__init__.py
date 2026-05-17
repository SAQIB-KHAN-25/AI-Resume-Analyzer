"""Backend package initialization.

Loads environment variables from the project root .env file so local runs
pick up MongoDB and auth settings consistently.
"""

from pathlib import Path

from dotenv import load_dotenv

ROOT_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ROOT_ENV_FILE)

