import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
APP_TITLE = os.getenv("APP_TITLE", "Transaction Comparison AI")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
FUZZY_THRESHOLD = float(os.getenv("FUZZY_THRESHOLD", "85"))
AMOUNT_TOLERANCE_PCT = float(os.getenv("AMOUNT_TOLERANCE_PCT", "2.0"))

GEMINI_MODEL = "gemini-2.0-flash"
