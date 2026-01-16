import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.chatwoot_base_url = os.getenv("CHATWOOT_BASE_URL", "").rstrip("/")
        self.chatwoot_account_id = os.getenv("CHATWOOT_ACCOUNT_ID", "")
        self.chatwoot_inbox_id = os.getenv("CHATWOOT_INBOX_ID", "")
        self.chatwoot_api_token = os.getenv("CHATWOOT_API_TOKEN", "")

        self.unipile_base_url = os.getenv(
            "UNIPILE_BASE_URL", "https://api26.unipile.com:15609/api/v1"
        ).rstrip("/")
        self.unipile_api_key = os.getenv("UNIPILE_API_KEY", "")

        self.supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

        self.webhook_secret = os.getenv("WEBHOOK_SECRET", "")
        self.dedupe_ttl_seconds = int(os.getenv("DEDUPE_TTL_SECONDS", "120"))
        self.request_timeout_seconds = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
        self.request_retries = int(os.getenv("REQUEST_RETRIES", "2"))

        self.log_level = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
