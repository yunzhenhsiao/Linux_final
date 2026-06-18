# skeleton/tasks.py
import sys
from pathlib import Path

# Ensure project root (/app inside container, repo root locally) is in sys.path
# so that `from databases.relational.queries import ...` resolves correctly
# when Celery worker loads this module.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from celery import Celery
from celery.schedules import crontab
from skeleton.config import REDIS_HOST, REDIS_PORT


# ── Celery application ────────────────────────────────────────────────────────
app = Celery(
    "transitflow",
    broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
    backend=f"redis://{REDIS_HOST}:{REDIS_PORT}/2",
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Taipei",   # 排程符合台灣本地時間
    enable_utc=False,
)

# ── Beat / Cron Schedule ──────────────────────────────────────────────────────
app.conf.beat_schedule = {
    "generate-daily-report": {
        "task": "skeleton.tasks.generate_daily_report",
        "schedule": crontab(hour=0, minute=0),   # 台灣時間每日午夜 00:00
    },
    "cleanup-old-sessions": {
        "task": "skeleton.tasks.cleanup_old_sessions",
        "schedule": crontab(hour=2, minute=0),   # 台灣時間每日凌晨 02:00
    },
}


# ── Tasks ─────────────────────────────────────────────────────────────────────

@app.task(bind=True)
def generate_daily_report(self):
    """Generate system operations report asynchronously."""
    try:
        from databases.relational.queries import query_admin_system_stats

        stats = query_admin_system_stats()
        print(f"Daily report generated: {stats}")
        return {
            "status": "completed",
            "message": "Daily report generated successfully",
            "data": stats,
        }
    except Exception as e:
        print(f"Daily report failed: {e}")
        raise


@app.task(bind=True)
def cleanup_old_sessions(self):
    """Clean up expired user sessions daily at 2 AM (Asia/Taipei)."""
    try:
        from databases.relational.queries import delete_old_sessions

        deleted_count = delete_old_sessions(days=30)
        print(f"Cleaned up {deleted_count} old sessions.")
        return {
            "status": "completed",
            "message": "Old sessions cleaned up successfully",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        print(f"Cleanup old sessions failed: {e}")
        raise


@app.task(bind=True)
def send_bulk_notification(self, user_ids: list, message: str):
    """Batch dispatch notifications to user base."""
    try:
        from databases.relational.queries import send_notification

        for user_id in user_ids:
            send_notification(user_id, message)

        return {
            "status": "completed",
            "message": f"Sent notification to {len(user_ids)} users",
            "count": len(user_ids),
        }
    except Exception as e:
        print(f"Send bulk notification failed: {e}")
        raise


@app.task(bind=True)
def update_user_roles_bulk(self, role_mapping: dict):
    """Batch update user roles (user_id -> new_role)."""
    try:
        from databases.relational.queries import query_admin_update_user_role

        total = 0
        for user_id, new_role in role_mapping.items():
            query_admin_update_user_role(user_id, new_role)
            total += 1

        return {
            "status": "completed",
            "message": f"Updated {total} users",
            "count": total,
        }
    except Exception as e:
        print(f"Update user roles failed: {e}")
        raise
