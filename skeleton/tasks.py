# skeleton/tasks.py
from celery import Celery, shared_task
from celery.schedules import crontab
import os
from skeleton.config import REDIS_HOST, REDIS_PORT

# Initialize Celery
app = Celery(
    'transitflow',
    broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/1',
    backend=f'redis://{REDIS_HOST}:{REDIS_PORT}/2'
)

# Configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Beat / Cron Schedule Configuration
app.conf.beat_schedule = {
    'generate-daily-report': {
        'task': 'skeleton.tasks.generate_daily_report',
        'schedule': crontab(hour=0, minute=0),  # daily at midnight
    },
    'cleanup-old-sessions': {
        'task': 'skeleton.tasks.cleanup_old_sessions',
        'schedule': crontab(hour=2, minute=0),  # daily at 2 AM
    },
}

@shared_task
def generate_daily_report():
    """Generate system operations report asynchronously."""
    from databases.relational.queries import query_admin_system_stats
    
    stats = query_admin_system_stats()
    print(f"Daily report generated: {stats}")
    return {"status": "completed", "data": stats}

@shared_task
def cleanup_old_sessions():
    """Clean up expired user sessions daily at 2 AM."""
    from databases.relational.queries import delete_old_sessions
    
    deleted_count = delete_old_sessions(days=30)
    print(f"Cleaned up {deleted_count} old sessions.")
    return deleted_count

@shared_task
def send_bulk_notification(user_ids: list, message: str):
    """Batch dispatch notifications to user base."""
    from databases.relational.queries import send_notification
    
    for user_id in user_ids:
        send_notification(user_id, message)
    
    return f"Sent notification to {len(user_ids)} users."

@shared_task
def update_user_roles_bulk(role_mapping: dict):
    """Batch update user roles (user_id -> new_role)."""
    from databases.relational.queries import query_admin_update_user_role
    
    total = 0
    for user_id, new_role in role_mapping.items():
        query_admin_update_user_role(user_id, new_role)
        total += 1
    
    return f"Updated {total} users."
