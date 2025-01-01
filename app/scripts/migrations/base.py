from datetime import datetime
from typing import List


class Migration:
    """Base migration class"""

    version: str
    description: str

    @classmethod
    async def up(cls, db):
        """Run migration"""
        raise NotImplementedError()

    @classmethod
    async def down(cls, db):
        """Rollback migration"""
        raise NotImplementedError()
