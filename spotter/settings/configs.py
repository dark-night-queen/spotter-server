from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE_CONFIG = {
    "env_file": (".env", ".env.local"),
    "env_file_encoding": "utf-8",
    "extra": "ignore",
}


class DatabaseConfigs(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="db_", **ENV_FILE_CONFIG)

    username: str
    password: str
    dbname: str
    port: str
    host: str


class Configs(BaseSettings):
    model_config = SettingsConfigDict(**ENV_FILE_CONFIG)

    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY: str
    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG: bool
    ALLOWED_HOSTS: str = "*"  # Accept as string from env

    DATABASE: DatabaseConfigs = DatabaseConfigs()

    GOOGLE_MAPS_API_KEY: str

    def model_post_init(self, __context):
        # Split ALLOWED_HOSTS string into a list
        if isinstance(self.ALLOWED_HOSTS, str):
            self.ALLOWED_HOSTS = self.ALLOWED_HOSTS.split()


db_configs = DatabaseConfigs()
configs = Configs()
