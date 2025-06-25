from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    opensearch_url: str
    opensearch_username: str
    opensearch_password: str
    typo_api_url: str

    class Config:
        env_file = ".env"


settings = Settings()