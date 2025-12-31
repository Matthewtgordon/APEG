"""Strategy tag mapping resolver for Meta entities.

Supports multiple methods:
- Method A: Explicit APEG creation tracking (preferred)
- Method B: Campaign/ad naming convention parsing
- Method C: Ad URL utm_campaign fetch (on-demand API call)
"""
import json
import logging
import re
import sqlite3
from enum import Enum
from typing import Optional


logger = logging.getLogger(__name__)


class MappingMethod(str, Enum):
    """Strategy tag mapping method."""

    APEG_TRACKING = "apeg_tracking"
    NAMING_CONVENTION = "naming_convention"
    UTM_FETCH = "utm_fetch"
    MANUAL = "manual"


class StrategyTagMapper:
    """Resolve Meta entity -> strategy_tag mappings."""

    def __init__(self, db_conn: sqlite3.Connection, strategy_catalog: list[str]):
        """Initialize mapper.

        Args:
            db_conn: SQLite connection
            strategy_catalog: List of valid strategy tags
        """
        self.db_conn = db_conn
        self.strategy_catalog = strategy_catalog

    def get_mapping(
        self, entity_type: str, entity_id: str, entity_name: Optional[str] = None
    ) -> Optional[tuple[str, MappingMethod, float]]:
        """Get strategy_tag for entity.

        Args:
            entity_type: 'campaign' or 'ad'
            entity_id: Meta entity ID
            entity_name: Campaign/ad name (for naming convention fallback)

        Returns:
            (strategy_tag, method, confidence) or None
        """
        cursor = self.db_conn.execute(
            """
            SELECT strategy_tag, mapping_method, mapping_confidence
            FROM strategy_tag_mappings
            WHERE entity_type=? AND entity_id=?
            """,
            (entity_type, entity_id),
        )
        row = cursor.fetchone()

        if row:
            return (row[0], MappingMethod(row[1]), row[2])

        if entity_name:
            tag, confidence = self._parse_from_name(entity_name)
            if tag:
                return (tag, MappingMethod.NAMING_CONVENTION, confidence)

        return None

    def _parse_from_name(self, name: str) -> tuple[Optional[str], float]:
        """Parse strategy_tag from campaign/ad name.

        Convention: Name should contain strategy_tag slug.
        Example: "Birthstone January - Garnet Collection" -> "birthstone_january"

        Args:
            name: Campaign or ad name

        Returns:
            (strategy_tag, confidence) or (None, 0.0)
        """
        if not name:
            return (None, 0.0)

        name_lower = name.lower()

        for tag in self.strategy_catalog:
            if tag.lower() in name_lower:
                return (tag, 0.9)

        name_slug = re.sub(r"[\s\-]+", "_", name_lower)
        name_slug = re.sub(r"[^a-z0-9_]", "", name_slug)

        for tag in self.strategy_catalog:
            tag_slug = re.sub(r"[\s\-]+", "_", tag.lower())
            tag_slug = re.sub(r"[^a-z0-9_]", "", tag_slug)

            if tag_slug in name_slug:
                return (tag, 0.7)

        return (None, 0.0)

    def add_manual_mapping(
        self,
        entity_type: str,
        entity_id: str,
        strategy_tag: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Add or update manual mapping.

        Args:
            entity_type: 'campaign' or 'ad'
            entity_id: Meta entity ID
            strategy_tag: Target strategy tag
            metadata: Optional metadata (e.g., reason, source)
        """
        self.db_conn.execute(
            """
            INSERT INTO strategy_tag_mappings (
                entity_type, entity_id, strategy_tag,
                mapping_method, mapping_confidence, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_type, entity_id)
            DO UPDATE SET
                strategy_tag=excluded.strategy_tag,
                mapping_method=excluded.mapping_method,
                mapping_confidence=excluded.mapping_confidence,
                metadata_json=excluded.metadata_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                entity_type,
                entity_id,
                strategy_tag,
                MappingMethod.MANUAL.value,
                1.0,
                json.dumps(metadata or {}, separators=(",", ":")),
            ),
        )
        self.db_conn.commit()
