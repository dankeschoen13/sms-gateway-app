from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
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

class SMSReportTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """
        Heavy Database I/O: Runs exactly ONCE per class. Class method named "setUpTestData"
        is automatically executed by Django Testing Framework
        """
        today = timezone.now()
        five_days_ago = today - timedelta(days=5)
        twenty_days_ago = today - timedelta(days=20)

        messages_to_create = [
            Message(
                sender_number="+10000000001",
                message_body="help me",
                department="Support"
            ),
            Message(
                sender_number="+10000000002",
                message_body="billing issue",
                department="Billing"
            ),
            Message(
                sender_number="+10000000003",
                message_body="cancel my account",
                department="Cancellations"
            )
        ]

        Message.objects.bulk_create(messages_to_create)

        # auto_now_add date override
        Message.objects.filter(department="Billing").update(timestamp=five_days_ago)
        Message.objects.filter(department="Cancellations").update(timestamp=twenty_days_ago)

    def setUp(self):
        self.client = Client()
        self.url = reverse('sms_report')

    def test_daily_report_only_counts_today(self):

        response = self.client.get(self.url, data={'period': 'daily'})
        data = response.json()

        # Should only see the 1 message from today
        self.assertEqual(data['total_messages_processed'], 1)
        self.assertIn('Support', data['department_breakdown'])
        self.assertNotIn('Billing', data['department_breakdown'])

    def test_weekly_report_includes_last_five_days(self):

        response = self.client.get(self.url, data={'period': 'weekly'})
        data = response.json()

        # Should see today (1) + 5 days ago (1) = 2 total
        self.assertEqual(data['total_messages_processed'], 2)
        self.assertEqual(data['department_breakdown']['Support'], 1)
        self.assertEqual(data['department_breakdown']['Billing'], 1)
        self.assertNotIn('Cancellations', data['department_breakdown'])

    def test_monthly_report_includes_all_records(self):

        response = self.client.get(self.url, data={'period': 'monthly'})
        data = response.json()

        # Should see all 3 messages
        self.assertEqual(data['total_messages_processed'], 3)
        self.assertEqual(data['department_breakdown']['Cancellations'], 1)



