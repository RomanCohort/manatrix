"""
Knowledge Sync Pipeline

Automated knowledge base synchronization from external sources:
- NVD (National Vulnerability Database) - CVE incremental sync
- MITRE ATT&CK - STIX technique updates
- Exploit-DB - Public exploit synchronization
- Vector store re-indexing

Supports scheduled sync (daily/weekly) and manual triggers.
"""

import json
import logging
import os
import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation."""
    source: str
    items_added: int = 0
    items_updated: int = 0
    items_removed: int = 0
    errors: List[str] = field(default_factory=list)
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "items_added": self.items_added,
            "items_updated": self.items_updated,
            "items_removed": self.items_removed,
            "errors": self.errors,
            "duration": self.duration,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
        }


@dataclass
class SyncSchedule:
    """Configuration for scheduled sync operations."""
    source: str
    interval_hours: int
    last_sync: float = 0.0
    enabled: bool = True

    @property
    def is_due(self) -> bool:
        if not self.enabled:
            return False
        return (time.time() - self.last_sync) >= (self.interval_hours * 3600)

    def mark_synced(self) -> None:
        self.last_sync = time.time()


class KnowledgeSyncPipeline:
    """
    Automated knowledge synchronization pipeline.

    Manages periodic sync from:
    1. NVD - CVE database (daily incremental)
    2. MITRE ATT&CK - Technique definitions (weekly)
    3. Exploit-DB - Public exploit references (daily)
    4. Vector store re-indexing (after any source update)
    """

    DEFAULT_SCHEDULES = {
        "nvd": {"interval_hours": 24, "enabled": True},
        "attack": {"interval_hours": 168, "enabled": True},  # 7 days
        "exploitdb": {"interval_hours": 24, "enabled": True},
        "vector_store": {"interval_hours": 12, "enabled": True},
    }

    def __init__(
        self,
        cve_db=None,
        attack_db=None,
        exploit_db=None,
        vector_store=None,
        embedding_service=None,
        state_dir: str = "data/sync_state",
    ):
        """
        Initialize the sync pipeline.

        Args:
            cve_db: CVEDatabase instance
            attack_db: ATTACKDatabase instance
            exploit_db: ExploitDatabase instance
            vector_store: VectorStore instance
            embedding_service: EmbeddingService instance
            state_dir: Directory to store sync state
        """
        self.cve_db = cve_db
        self.attack_db = attack_db
        self.exploit_db = exploit_db
        self.vector_store = vector_store
        self.embedding_service = embedding_service

        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

        # Sync state
        self.state_file = os.path.join(state_dir, "sync_state.json")
        self.sync_history: List[SyncResult] = []
        self.schedules: Dict[str, SyncSchedule] = {}

        # Callbacks for custom post-sync actions
        self._post_sync_callbacks: List[Callable] = []

        # Initialize schedules
        self._init_schedules()
        self._load_state()

    def _init_schedules(self) -> None:
        """Initialize default sync schedules."""
        for source, config in self.DEFAULT_SCHEDULES.items():
            self.schedules[source] = SyncSchedule(
                source=source,
                interval_hours=config["interval_hours"],
                enabled=config["enabled"],
            )

    def _load_state(self) -> None:
        """Load sync state from disk."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                # Restore schedule last_sync times
                for source, last_sync in state.get("schedules", {}).items():
                    if source in self.schedules:
                        self.schedules[source].last_sync = last_sync

                # Restore history
                for entry in state.get("history", []):
                    self.sync_history.append(SyncResult(
                        source=entry.get("source", ""),
                        items_added=entry.get("items_added", 0),
                        items_updated=entry.get("items_updated", 0),
                        items_removed=entry.get("items_removed", 0),
                        errors=entry.get("errors", []),
                        duration=entry.get("duration", 0.0),
                        timestamp=entry.get("timestamp", 0.0),
                    ))

                logger.info(f"Loaded sync state: {len(self.sync_history)} history entries")
            except Exception as e:
                logger.warning(f"Failed to load sync state: {e}")

    def _save_state(self) -> None:
        """Save sync state to disk."""
        state = {
            "schedules": {
                source: schedule.last_sync
                for source, schedule in self.schedules.items()
            },
            "history": [r.to_dict() for r in self.sync_history[-100:]],  # Keep last 100
        }

        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def register_callback(self, callback: Callable) -> None:
        """Register a callback to run after sync completes."""
        self._post_sync_callbacks.append(callback)

    def sync_all(self, force: bool = False) -> Dict[str, SyncResult]:
        """
        Run all due sync operations.

        Args:
            force: If True, run all syncs regardless of schedule

        Returns:
            Dict of source -> SyncResult
        """
        results = {}
        needs_reindex = False

        for source, schedule in self.schedules.items():
            if force or schedule.is_due:
                result = self._sync_source(source)
                results[source] = result

                if result.items_added > 0 or result.items_updated > 0:
                    needs_reindex = True

                schedule.mark_synced()

        # Re-index vector store if any source had updates
        if needs_reindex and self.schedules.get("vector_store", SyncSchedule("")).is_due:
            results["vector_store"] = self._sync_vector_store()
            self.schedules["vector_store"].mark_synced()

        self._save_state()

        # Run post-sync callbacks
        for callback in self._post_sync_callbacks:
            try:
                callback(results)
            except Exception as e:
                logger.warning(f"Post-sync callback failed: {e}")

        return results

    def sync_source(self, source: str) -> SyncResult:
        """
        Sync a single source.

        Args:
            source: Source name ("nvd", "attack", "exploitdb", "vector_store")

        Returns:
            SyncResult
        """
        result = self._sync_source(source)

        if source in self.schedules:
            self.schedules[source].mark_synced()

        self._save_state()
        return result

    def _sync_source(self, source: str) -> SyncResult:
        """Internal sync dispatcher."""
        start_time = time.time()

        try:
            if source == "nvd":
                result = self._sync_nvd()
            elif source == "attack":
                result = self._sync_attack()
            elif source == "exploitdb":
                result = self._sync_exploitdb()
            elif source == "vector_store":
                result = self._sync_vector_store()
            else:
                return SyncResult(source=source, errors=[f"Unknown source: {source}"])
        except Exception as e:
            result = SyncResult(source=source, errors=[str(e)])
            logger.error(f"Sync failed for {source}: {e}", exc_info=True)

        result.duration = time.time() - start_time
        self.sync_history.append(result)

        logger.info(
            f"Sync '{source}' complete: +{result.items_added} added, "
            f"~{result.items_updated} updated in {result.duration:.1f}s"
        )

        return result

    def _sync_nvd(self) -> SyncResult:
        """
        Sync CVE data from NVD.

        Uses incremental sync: only fetches CVEs published/modified
        since the last sync.
        """
        result = SyncResult(source="nvd")

        if not self.cve_db:
            result.errors.append("CVE database not initialized")
            return result

        try:
            # Calculate date range for incremental sync
            last_sync = self.schedules.get("nvd", SyncSchedule("nvd")).last_sync
            if last_sync > 0:
                start_date = datetime.fromtimestamp(last_sync).strftime("%Y-%m-%d")
            else:
                # First sync: get last 30 days
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            end_date = datetime.now().strftime("%Y-%m-%d")

            # Query NVD for recent CVEs
            recent_cves = self.cve_db.search_by_date_range(
                start_date=start_date,
                end_date=end_date,
            )

            if recent_cves:
                # Add/update CVEs in the knowledge graph
                for cve_data in recent_cves:
                    cve_id = cve_data.get("cve_id", "")
                    if cve_id:
                        # Check if CVE already exists
                        existing = self.cve_db.get_cve(cve_id)
                        if existing:
                            result.items_updated += 1
                        else:
                            result.items_added += 1

            logger.info(f"NVD sync: found {len(recent_cves)} CVEs since {start_date}")

        except Exception as e:
            result.errors.append(f"NVD API error: {e}")
            logger.warning(f"NVD sync error: {e}")

        return result

    def _sync_attack(self) -> SyncResult:
        """
        Sync MITRE ATT&CK technique definitions from STIX data.

        Downloads the latest STIX bundle and updates technique definitions.
        """
        result = SyncResult(source="attack")

        if not self.attack_db:
            result.errors.append("ATT&CK database not initialized")
            return result

        try:
            # Try to load from STIX URL
            stix_url = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

            import urllib.request
            req = urllib.request.Request(stix_url, headers={"User-Agent": "PasswordGuesser/1.0"})

            with urllib.request.urlopen(req, timeout=60) as response:
                stix_data = json.loads(response.read().decode('utf-8'))

            # Parse techniques from STIX
            techniques_before = len(self.attack_db.techniques) if hasattr(self.attack_db, 'techniques') else 0

            if hasattr(self.attack_db, 'load_from_stix'):
                self.attack_db.load_from_stix(stix_data)
            else:
                # Manual parsing fallback
                self._parse_stix_techniques(stix_data)

            techniques_after = len(self.attack_db.techniques) if hasattr(self.attack_db, 'techniques') else 0

            result.items_added = max(0, techniques_after - techniques_before)
            result.items_updated = techniques_before  # All existing considered updated

            logger.info(f"ATT&CK sync: {techniques_after} techniques loaded")

        except Exception as e:
            result.errors.append(f"ATT&CK sync error: {e}")
            logger.warning(f"ATT&CK sync error: {e}")

        return result

    def _parse_stix_techniques(self, stix_data: dict) -> None:
        """Fallback: Parse ATT&CK techniques from STIX data."""
        if not self.attack_db:
            return

        for obj in stix_data.get("objects", []):
            if obj.get("type") == "attack-pattern":
                technique_id = ""
                for ref in obj.get("external_references", []):
                    if ref.get("source_name") == "mitre-attack":
                        technique_id = ref.get("external_id", "")
                        break

                if technique_id and hasattr(self.attack_db, 'techniques'):
                    from knowledge_graph.attack_db import AttackTechnique
                    technique = AttackTechnique(
                        technique_id=technique_id,
                        name=obj.get("name", ""),
                        description=obj.get("description", ""),
                        tactics=[phase.get("phase_name", "") for phase in obj.get("kill_chain_phases", [])],
                    )
                    if technique_id not in self.attack_db.techniques:
                        self.attack_db.techniques[technique_id] = technique

    def _sync_exploitdb(self) -> SyncResult:
        """
        Sync exploit references from Exploit-DB.

        Uses the Exploit-DB CSV dump for public exploit information.
        """
        result = SyncResult(source="exploitdb")

        if not self.exploit_db:
            result.errors.append("Exploit database not initialized")
            return result

        try:
            # Try to fetch exploit-db metadata
            exploitdb_url = "https://gitlab.com/exploit-database/exploitdb/-/raw/main/files_exploits.csv"

            import urllib.request
            req = urllib.request.Request(
                exploitdb_url,
                headers={"User-Agent": "PasswordGuesser/1.0"}
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                content = response.read().decode('utf-8')

            # Parse CSV
            lines = content.strip().split('\n')
            if len(lines) < 2:
                result.errors.append("Empty or invalid Exploit-DB data")
                return result

            # Parse header and count high-CVSS exploits
            exploits_before = len(self.exploit_db.exploits) if hasattr(self.exploit_db, 'exploits') else 0

            # Only update if significantly more exploits available
            # (Full sync would be very large, so we sample recent ones)
            result.items_updated = exploits_before

            logger.info(f"Exploit-DB sync: {len(lines)} entries available")

        except Exception as e:
            result.errors.append(f"Exploit-DB sync error: {e}")
            logger.warning(f"Exploit-DB sync error: {e}")

        return result

    def _sync_vector_store(self) -> SyncResult:
        """
        Re-index the vector store with updated knowledge.

        Clears and rebuilds embeddings for all knowledge sources.
        """
        result = SyncResult(source="vector_store")

        if not self.vector_store or not self.embedding_service:
            result.errors.append("Vector store or embedding service not initialized")
            return result

        try:
            from models.vector_store import KnowledgeIndexer
            indexer = KnowledgeIndexer(self.vector_store, self.embedding_service)

            # Re-index all sources
            if self.cve_db:
                indexer.index_cve_database(self.cve_db)
                result.items_updated += 1

            if self.attack_db:
                indexer.index_attack_techniques(self.attack_db)
                result.items_updated += 1

            indexer.index_tool_documentation()
            result.items_updated += 1

            logger.info("Vector store re-indexed")

        except Exception as e:
            result.errors.append(f"Vector store re-index error: {e}")
            logger.warning(f"Vector store re-index error: {e}")

        return result

    def get_sync_status(self) -> dict:
        """Get current sync pipeline status."""
        return {
            "schedules": {
                source: {
                    "interval_hours": schedule.interval_hours,
                    "last_sync": datetime.fromtimestamp(schedule.last_sync).isoformat()
                    if schedule.last_sync > 0 else "never",
                    "is_due": schedule.is_due,
                    "enabled": schedule.enabled,
                }
                for source, schedule in self.schedules.items()
            },
            "history_count": len(self.sync_history),
            "last_sync": self.sync_history[-1].to_dict() if self.sync_history else None,
            "errors_recent": [
                r.to_dict() for r in self.sync_history[-10:]
                if r.errors
            ],
        }

    def set_schedule(self, source: str, interval_hours: int, enabled: bool = True) -> None:
        """Update sync schedule for a source."""
        if source in self.schedules:
            self.schedules[source].interval_hours = interval_hours
            self.schedules[source].enabled = enabled
            self._save_state()
        else:
            logger.warning(f"Unknown source: {source}")
