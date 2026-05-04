import os
from flask import Flask, request, jsonify, send_from_directory
from sqlalchemy import desc
from database import SessionLocal, Base, engine
from models import WebhookTask, TaskStatus
import tasks

app = Flask(__name__)

# Initialize database
Base.metadata.create_all(bind=engine)

@app.route("/")
def index():
    return send_from_directory('static', 'index.html')

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory('static', path)

@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    db = SessionLocal()
    try:
        tasks = db.query(WebhookTask).order_by(desc(WebhookTask.created_at)).limit(50).all()
        return jsonify([{
            "task_id": task.id,
            "status": task.status.value,
            "retry_count": task.retry_count,
            "target_url": task.target_url,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat()
        } for task in tasks]), 200
    finally:
        db.close()

@app.route("/api/stats", methods=["GET"])
def get_stats():
    db = SessionLocal()
    try:
        total = db.query(WebhookTask).count()
        success = db.query(WebhookTask).filter(WebhookTask.status == TaskStatus.SUCCESS).count()
        failed = db.query(WebhookTask).filter(WebhookTask.status == TaskStatus.FAILED).count()
        retrying = db.query(WebhookTask).filter(WebhookTask.status == TaskStatus.RETRYING).count()
        pending = db.query(WebhookTask).filter(WebhookTask.status == TaskStatus.PENDING).count()
        
        return jsonify({
            "total": total,
            "success": success,
            "failed": failed,
            "retrying": retrying,
            "pending": pending
        }), 200
    finally:
        db.close()

@app.route("/send-webhook", methods=["POST"])
def send_webhook():
    data = request.json
    if not data or "target_url" not in data or "payload" not in data:
        return jsonify({"error": "Missing target_url or payload"}), 400

    target_url = data["target_url"]
    payload = data["payload"]

    db = SessionLocal()
    try:
        # 1. Create task in DB
        new_task = WebhookTask(target_url=target_url, payload=payload)
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        # 2. Enqueue task in Celery
        tasks.deliver_webhook.delay(new_task.id)

        # 3. Return 202 Accepted
        return jsonify({
            "message": "Webhook queued for delivery",
            "task_id": new_task.id
        }), 202
    finally:
        db.close()


@app.route("/status/<task_id>", methods=["GET"])
def get_status(task_id):
    db = SessionLocal()
    try:
        task = db.query(WebhookTask).filter(WebhookTask.id == task_id).first()
        if not task:
            return jsonify({"error": "Task not found"}), 404
        
        return jsonify({
            "task_id": task.id,
            "status": task.status.value,
            "retry_count": task.retry_count,
            "target_url": task.target_url,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat()
        }), 200
    finally:
        db.close()

if __name__ == "__main__":
    app.run(port=5000, debug=True)
