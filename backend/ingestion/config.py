import os
from dotenv import load_dotenv


load_dotenv()


def get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def marketcheck_config() -> dict:
    return {
        "api_key": get_env("MARKETCHECK_API_KEY"),
        "base_url": get_env("MARKETCHECK_BASE_URL", "https://api.marketcheck.com/v2"),
        "country": get_env("MARKETCHECK_COUNTRY", "us"),
        "radius": get_env("MARKETCHECK_RADIUS", "250"),
        "rows": get_env("MARKETCHECK_ROWS", "25"),
        "start": get_env("MARKETCHECK_START", "0"),
    }


