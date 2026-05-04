import os
import requests
from celery import Celery
from database import SessionLocal
from models import WebhookTask, TaskStatus

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery
# We use a filesystem broker fallback for local development if Redis is unavailable
celery_app = Celery("webhook_worker", broker=REDIS_URL)

try:
    # Test Redis connection (optional, but good for fallback logic)
    import redis
    r = redis.from_url(REDIS_URL)
    r.ping()
except Exception:
    # Fallback to filesystem broker for zero-infrastructure demo
    print("Redis not found. Falling back to filesystem broker for local demo...")
    os.makedirs("./broker/out", exist_ok=True)
    os.makedirs("./broker/processed", exist_ok=True)
    celery_app.conf.update(
        broker_url='filesystem://',
        broker_transport_options={
            'data_folder_in': './broker/out',
            'data_folder_out': './broker/out',
            'data_folder_processed': './broker/processed'
        }
    )

celery_app.conf.update(
    result_backend="rpc://",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Exponential backoff settings
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

@celery_app.task(bind=True, max_retries=5)
def deliver_webhook(self, task_id):
    db = SessionLocal()
    try:
        task = db.query(WebhookTask).filter(WebhookTask.id == task_id).first()
        if not task:
            print(f"Task {task_id} not found in DB.")
            return

        print(f"Attempting to deliver webhook {task_id} to {task.target_url}")

        # Send HTTP request
        response = requests.post(
            task.target_url, 
            json=task.payload,
            timeout=10
        )
        
        # Check if successful
        response.raise_for_status()

        # Success!
        task.status = TaskStatus.SUCCESS
        db.commit()
        print(f"Successfully delivered webhook {task_id}")

    except (requests.exceptions.RequestException, Exception) as exc:
        print(f"Failed to deliver webhook {task_id}: {str(exc)}")
        
        # Exponential backoff: 2 ^ retry_count seconds (e.g., 2s, 4s, 8s, 16s, 32s)
        retry_delay = 2 ** self.request.retries
        
        try:
            # Update DB status before retrying
            if task:
                task.status = TaskStatus.RETRYING
                task.retry_count = self.request.retries + 1
                db.commit()
            
            # This will raise Retry exception to Celery
            self.retry(exc=exc, countdown=retry_delay)
            
        except self.MaxRetriesExceededError:
            # Moved to Dead Letter Queue effectively by marking as FAILED
            if task:
                task.status = TaskStatus.FAILED
                db.commit()
            print(f"Max retries exceeded for task {task_id}. Marked as FAILED.")
    finally:
        db.close()
