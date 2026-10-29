import os

os.environ["DOCBRIEF_NO_DOTENV"] = "1"  # never read a real .env in tests
os.environ.pop("NEBIUS_API_KEY", None)
