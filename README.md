# Reliable Webhook Delivery System

A fault-tolerant webhook delivery system built with Python, Flask, Celery, Redis, and PostgreSQL. Designed to demonstrate enterprise-level asynchronous task processing and system resilience.

## Architecture

This system uses an Event-Driven Architecture to decouple the API from the actual delivery of webhooks.

1.  **API Gateway (Flask):** Instantly accepts the webhook payload, saves a `PENDING` record in the database, and pushes a task to the message broker. Returns `202 Accepted` to the client.
2.  **Message Broker (Redis):** Holds the queue of webhooks waiting to be delivered.
3.  **Background Workers (Celery):** Picks up tasks from Redis and attempts to send the HTTP POST request to the target URL.
4.  **Exponential Backoff:** If the target server is down or returns a 5xx error, the worker will retry with exponential backoff (2s, 4s, 8s...).
5.  **Database (PostgreSQL):** Acts as the source of truth and audit log for every webhook's status (`SUCCESS`, `FAILED`, `RETRYING`).

## Tech Stack
*   **Language:** Python 3.13
*   **Web Framework:** Flask
*   **Task Queue:** Celery
*   **Broker:** Redis
*   **Database:** PostgreSQL
*   **ORM:** SQLAlchemy (with `pg8000` pure-Python driver)

## Running Locally

1.  **Start Services (Redis & Postgres):**
    ```bash
    docker-compose up -d
    ```

2.  **Setup Environment:**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Run the API:**
    ```bash
    python app.py
    ```

4.  **Run the Celery Worker:**
    Open a new terminal, activate the venv, and run:
    ```bash
    celery -A tasks.celery_app worker --loglevel=info -P solo
    ```
    *(Note: `-P solo` is required on Windows for Celery)*

## API Endpoints

### 1. Send a Webhook
`POST /send-webhook`
```json
{
    "target_url": "https://httpbin.org/post",
    "payload": {
        "event": "user.created",
        "user_id": 123
    }
}
```

### 2. Check Status
`GET /status/<task_id>`
Returns the status (`PENDING`, `SUCCESS`, `RETRYING`, `FAILED`) and retry count.
