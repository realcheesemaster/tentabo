"""
Pennylane Background Sync Scheduler

Provides automatic background synchronization of Pennylane data for all active connections.
Uses APScheduler with AsyncIOScheduler for non-blocking periodic tasks.

Configuration via environment variables:
- ENABLE_PENNYLANE_SCHEDULER: Enable/disable scheduler (default: false)
- PENNYLANE_SYNC_INTERVAL_HOURS: Sync interval in hours (default: 6)
"""

import logging
import os
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import SessionLocal
from app.models.pennylane import PennylaneConnection
from app.services.pennylane_service import PennylaneSyncService, SyncResult

logger = logging.getLogger(__name__)

# Module-level scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_sync_interval_hours() -> int:
    """
    Get the sync interval from environment variable.

    Returns:
        int: Sync interval in hours (default: 6)
    """
    try:
        return int(os.getenv("PENNYLANE_SYNC_INTERVAL_HOURS", "6"))
    except ValueError:
        logger.warning("Invalid PENNYLANE_SYNC_INTERVAL_HOURS value, using default of 6 hours")
        return 6


def is_scheduler_enabled() -> bool:
    """
    Check if the scheduler is enabled via environment variable.

    Returns:
        bool: True if scheduler is enabled
    """
    return os.getenv("ENABLE_PENNYLANE_SCHEDULER", "false").lower() == "true"


async def sync_all_connections() -> dict[str, dict[str, SyncResult]]:
    """
    Sync all active Pennylane connections.

    Fetches all active PennylaneConnections from the database and runs
    sync_all() for each one. Errors in one connection do not affect others.

    Returns:
        Dictionary mapping connection name to sync results
    """
    logger.info("Starting scheduled Pennylane sync for all connections")
    results: dict[str, dict[str, SyncResult]] = {}

    # Create a new database session for this task
    db = SessionLocal()

    try:
        # Fetch all active connections
        connections = (
            db.query(PennylaneConnection)
            .filter(PennylaneConnection.is_active == True)
            .all()
        )

        if not connections:
            logger.info("No active Pennylane connections found")
            return results

        logger.info(f"Found {len(connections)} active Pennylane connection(s)")

        for connection in connections:
            connection_name = connection.name
            logger.info(f"Starting sync for connection: {connection_name}")

            try:
                # Create sync service for this connection
                # Need a fresh session for each connection to avoid conflicts
                sync_db = SessionLocal()
                try:
                    # Re-fetch connection in new session
                    conn = (
                        sync_db.query(PennylaneConnection)
                        .filter(PennylaneConnection.id == connection.id)
                        .first()
                    )

                    if conn is None:
                        logger.warning(f"Connection {connection_name} no longer exists")
                        continue

                    sync_service = PennylaneSyncService(sync_db, conn)
                    sync_results = await sync_service.sync_all()
                    results[connection_name] = sync_results

                    # Log summary for this connection
                    total_created = sum(r.created for r in sync_results.values())
                    total_updated = sum(r.updated for r in sync_results.values())
                    total_errors = sum(len(r.errors) for r in sync_results.values())

                    logger.info(
                        f"Sync complete for {connection_name}: "
                        f"created={total_created}, updated={total_updated}, errors={total_errors}"
                    )

                finally:
                    sync_db.close()

            except Exception as e:
                logger.error(f"Error syncing connection {connection_name}: {e}", exc_info=True)
                # Continue with next connection - don't let one failure stop others
                continue

    except Exception as e:
        logger.error(f"Error fetching Pennylane connections: {e}", exc_info=True)

    finally:
        db.close()

    logger.info(f"Scheduled Pennylane sync complete. Processed {len(results)} connection(s)")
    return results


def start_scheduler() -> None:
    """
    Start the background scheduler for Pennylane sync.

    Creates and starts an AsyncIOScheduler with the configured sync interval.
    This function should be called during FastAPI startup.

    The scheduler only starts if ENABLE_PENNYLANE_SCHEDULER=true.
    """
    global _scheduler

    if not is_scheduler_enabled():
        logger.info("Pennylane scheduler is disabled (ENABLE_PENNYLANE_SCHEDULER != true)")
        return

    if _scheduler is not None and _scheduler.running:
        logger.warning("Pennylane scheduler is already running")
        return

    interval_hours = get_sync_interval_hours()
    logger.info(f"Starting Pennylane scheduler with {interval_hours} hour interval")

    # Create the scheduler
    _scheduler = AsyncIOScheduler()

    # Add the sync job
    _scheduler.add_job(
        sync_all_connections,
        trigger=IntervalTrigger(hours=interval_hours),
        id="pennylane_sync_all",
        name="Pennylane Full Sync",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
        coalesce=True,  # Combine missed runs into one
    )

    # Start the scheduler
    _scheduler.start()
    logger.info("Pennylane scheduler started successfully")


def stop_scheduler() -> None:
    """
    Stop the background scheduler gracefully.

    Shuts down the scheduler and waits for any running jobs to complete.
    This function should be called during FastAPI shutdown.
    """
    global _scheduler

    if _scheduler is None:
        logger.debug("Pennylane scheduler was not initialized")
        return

    if not _scheduler.running:
        logger.debug("Pennylane scheduler is not running")
        return

    logger.info("Stopping Pennylane scheduler...")
    _scheduler.shutdown(wait=True)
    _scheduler = None
    logger.info("Pennylane scheduler stopped")


def get_scheduler_status() -> dict:
    """
    Get the current status of the scheduler.

    Returns:
        Dictionary with scheduler status information
    """
    global _scheduler

    if _scheduler is None:
        return {
            "enabled": is_scheduler_enabled(),
            "running": False,
            "jobs": [],
        }

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
        })

    return {
        "enabled": is_scheduler_enabled(),
        "running": _scheduler.running,
        "interval_hours": get_sync_interval_hours(),
        "jobs": jobs,
    }
