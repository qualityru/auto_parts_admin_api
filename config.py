import pathlib

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = pathlib.Path(__file__).parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    DB_HOST: str = Field("127.0.0.1", env="DB_HOST")
    DB_PORT: int = Field(5432, env="DB_PORT")
    DB_USER: str = Field("autoparts", env="DB_USER")
    DB_PASS: str = Field("autoparts", env="DB_PASS")
    DB_NAME: str = Field("autoparts", env="DB_NAME")

    SECRET_KEY: str = Field("admin-secret-change-me", env="SECRET_KEY")
    ADMIN_LOGIN: str = Field("admin", env="ADMIN_LOGIN")
    ADMIN_PASSWORD: str = Field("admin", env="ADMIN_PASSWORD")
    ADMIN_TOKEN_EXPIRES: int = Field(86400, env="ADMIN_TOKEN_EXPIRES")
    MARKUP_PART: int = Field(30, env="MARKUP_PART")

    BROKER_URL: str = Field(
        "amqp://guest:guest@127.0.0.1:5672/", env="BROKER_URL"
    )
    BROKER_EXCHANGE: str = Field(
        "autoparts.events", env="BROKER_EXCHANGE"
    )
    BROKER_ORDER_STATUS_ROUTING_KEY: str = Field(
        "orders.status.changed", env="BROKER_ORDER_STATUS_ROUTING_KEY"
    )
    BROKER_ORDER_CREATED_ROUTING_KEY: str = Field(
        "orders.created", env="BROKER_ORDER_CREATED_ROUTING_KEY"
    )

    @property
    def DB_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH), env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
