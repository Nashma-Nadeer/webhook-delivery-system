import unittest
import json
from app import app
from database import Base, engine, SessionLocal
from models import WebhookTask

class WebhookDeliveryTestCase(unittest.TestCase):
    def setUp(self):
        # Create a test client
        self.app = app.test_client()
        self.app.testing = True
        
        # Setup the database for testing
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_send_webhook_missing_data(self):
        response = self.app.post('/send-webhook', json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", json.loads(response.data))

    def test_send_webhook_success(self):
        payload = {
            "target_url": "https://httpbin.org/post",
            "payload": {"key": "value"}
        }
        response = self.app.post('/send-webhook', json=payload)
        self.assertEqual(response.status_code, 202)
        
        data = json.loads(response.data)
        self.assertIn("task_id", data)
        self.assertIn("message", data)

        # Check if it was inserted in the DB
        task = self.db.query(WebhookTask).filter(WebhookTask.id == data["task_id"]).first()
        self.assertIsNotNone(task)
        self.assertEqual(task.status.value, "PENDING")

if __name__ == '__main__':
    unittest.main()
