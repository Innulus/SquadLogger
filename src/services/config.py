from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
# We create a globally accessible settings object from the .env file.
# This ensures that we do not have to constantly rewrite .env fetch logic. 

class Settings(BaseSettings):
    PROD_DB_PATH: str 
    WEB_PORT: int
    MAX_LOG_CHUNK_SIZE: int
    API_SECRET_CODE: str
    ENVIRONMENT: str 
    
    model_config = SettingsConfigDict(env_file=".env")

BASE_DIR = Path(__file__).resolve().parent.parent

settings = Settings()

