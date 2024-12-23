import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "FastAPI Shop"
    PROJECT_VERSION: str = "1.0.0"

    MONGODB_URL: str = os.getenv(
        "MONGODB_URL", "mongodb://admin:password@localhost:27017"
    )
    DB_NAME: str = os.getenv("MONGODB_DB", "fastapi-shop")

    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )


settings = Settings()
