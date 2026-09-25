import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

def reload_env():
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        user_env = Path.home() / ".myclaude" / ".env"
        if user_env.exists():
            load_dotenv(user_env, override=True)


reload_env()


@dataclass
class Config:
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    model_name: str = "deepseek-chat"
    max_steps: int = 30
    auto_confirm: bool = False
    timeout: int = 60

    @classmethod
    def load(cls) -> "Config":
        reload_env()
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
            model_name=os.getenv("MODEL_NAME", "deepseek-chat"),
            max_steps=int(os.getenv("MAX_STEPS", "30")),
            auto_confirm=os.getenv("AUTO_CONFIRM", "false").lower() in ("true", "1", "yes"),
            timeout=int(os.getenv("CMD_TIMEOUT", "60")),
        )

    def is_configured(self) -> bool:
        return bool(self.api_key.strip())
