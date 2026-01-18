"""Repository layer for data persistence.

Provides repository classes for persisting domain data to the database.
Repositories encapsulate data access logic and provide a clean interface
for the service layer.
"""

from src.repositories.mapping_repo import MappingRepository

__all__ = [
    "MappingRepository",
]
