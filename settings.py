import os

from pydantic import BaseSettings, Field
from typing import Final

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Settings(BaseSettings):
    IP: Final[str] = Field(..., env='IP')
    PORT: Final[int] = Field(..., env='PORT')

    class Config:
        env_file = os.path.join(BASE_DIR, '.env')
        env_file_encoding = 'utf-8'
