from django.test import TestCase, Client
from django.urls import reverse
from .models import Message
import json

class SMSWebhookTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('sms_webhook')

    def test_successful_message_and_routing(self):
        """
        Test that a valid payload is saved and correctly routed.
        """
        payload = {
            "sender_number": "+1234567890",
            "message_body": "I need help with my invoice."
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)

        response_data = response.json()

        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['department_routed'], 'Billing')

        saved_message = Message.objects.first()

        self.assertIsInstance(saved_message, Message)
        self.assertEqual(saved_message.department, 'Billing')
        self.assertFalse(saved_message.is_blocked)
        self.assertEqual(Message.objects.count(), 1)

    def test_rate_limiting_blocks_excessive_requests(self):
        """
        Test the sliding window rate limiter kicks in after 5 messages.
        """
        payload = {
            "sender_number": "+19999999999",
            "message_body": "Spam message"
        }

        # Send 5 valid requests
        for i in range(5):
            response = self.client.post(
                self.url,
                data=json.dumps(payload),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 201)

        # The 6th request should be blocked
        response_blocked = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response_blocked.status_code, 429)
        self.assertEqual(response_blocked.json()['error'], 'Too Many Requests')

        latest_message = Message.objects.filter(sender_number="+19999999999").last()

        self.assertIsInstance(latest_message, Message)
        self.assertTrue(latest_message.is_blocked)
        self.assertEqual(Message.objects.count(), 6)

    def test_missing_message_body(self):
        """
        Test the route sends an error if the message_body is missing
        """

        payload = {
            "sender_number": "+19999999999"
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Missing required fields')
        self.assertIsNone(Message.objects.first())

    def test_missing_phone_number(self):
        """
        Test the route sends an error if the sender_number is missing
        """

        payload = {
            "message_body": "Spam message"
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Missing required fields')
        self.assertIsNone(Message.objects.first())

    def test_invalid_method(self):
        """
        Test the route sends an error if the request method is invalid
        """
        payload = {
            "sender_number": "+19999999999",
            "message_body": "Spam message"
        }

        response = self.client.patch(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()['error'], 'Method not allowed')
        self.assertIsNone(Message.objects.first())

    def test_invalid_json_payload(self):
        """
        Test that malformed JSON is caught and returns a 400 Bad Request.
        """

        bad_json_string = '{"sender_number": "+1234567890", message_body: oops'

        response = self.client.post(
            self.url,
            data=bad_json_string,
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Invalid JSON payload')
        self.assertIsNone(Message.objects.first())

