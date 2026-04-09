import asyncpg

from src.library.adapters.out.repository import SkillFileRepo, SkillRepo
from src.library.app import LibraryApp


def build(pool: asyncpg.Pool) -> LibraryApp:
    return LibraryApp(SkillRepo(pool), SkillFileRepo(pool))
