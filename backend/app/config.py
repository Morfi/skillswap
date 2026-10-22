from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://skillswap:skillswap@db:5432/skillswap"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    admin_email: str = "admin@skillswap.dev"
    admin_password: str = "admin123"
    seed_demo_data: bool = True


settings = Settings()
