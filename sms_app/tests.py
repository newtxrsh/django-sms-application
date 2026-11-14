"""Tests for the SMS app.

textbee is never contacted: requests.post / requests.get are replaced with
mocks, so no real SMS is sent and no API key is needed to run the tests.
"""

from unittest import mock

import requests
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .forms import SMSForm
from .models import SMSMessage
from .services import REQUEST_TIMEOUT, get_sms_status, send_sms

FAKE_KEY = 'test-api-key-0000'
FAKE_DEVICE = 'device123'
TEXTBEE = override_settings(TEXTBEE_API_KEY=FAKE_KEY, TEXTBEE_DEVICE_ID=FAKE_DEVICE, TEXTBEE_SIM_SLOT='')

POST = 'sms_app.services.requests.post'
GET = 'sms_app.services.requests.get'


def fake_response(status_code, body=None, json_error=False):
    """Build a fake requests.Response."""
    response = mock.Mock(status_code=status_code)
    if json_error:
        response.json.side_effect = ValueError('not JSON')
    else:
        response.json.return_value = body
    return response


SEND_OK = fake_response(201, {'data': {'success': True, 'smsBatchId': 'batch123', 'recipientCount': 1}})


def batch_status(status, **extra):
    return fake_response(200, {'data': {'batch': {}, 'messages': [{'status': status, **extra}]}})


class FormValidationTests(TestCase):
    def form(self, recipient='+639171234567', message='Hello'):
        return SMSForm(data={'recipient': recipient, 'message': message})

    def test_valid_e164_number(self):
        form = self.form()
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['recipient'], '+639171234567')

    def test_empty_phone_is_rejected(self):
        form = self.form(recipient='')
        self.assertFalse(form.is_valid())
        self.assertIn("Please enter the recipient's phone number.", form.errors['recipient'])

    def test_empty_message_is_rejected(self):
        form = self.form(message='')
        self.assertFalse(form.is_valid())
        self.assertIn('Please enter a message.', form.errors['message'])

    def test_whitespace_only_message_is_rejected(self):
        form = self.form(message='   \n  ')
        self.assertFalse(form.is_valid())
        self.assertIn('Please enter a message.', form.errors['message'])

    def test_invalid_phone_formats_are_rejected(self):
        for number in ['12345', '09abc234567', '9171234567', '+63917123456', '+0639171234567']:
            with self.subTest(number=number):
                form = self.form(recipient=number)
                self.assertFalse(form.is_valid())
                self.assertIn('recipient', form.errors)

    def test_ph_local_format_is_normalized(self):
        form = self.form(recipient='09171234567')
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['recipient'], '+639171234567')

    def test_spaces_and_dashes_are_ignored(self):
        form = self.form(recipient='0917 123-4567')
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['recipient'], '+639171234567')

    def test_message_over_1600_characters_is_rejected(self):
        self.assertTrue(self.form(message='x' * 1600).is_valid())
        form = self.form(message='x' * 1601)
        self.assertFalse(form.is_valid())
        self.assertIn('maximum is 1600', form.errors['message'][0])

    def test_crlf_line_break_counts_as_one_character(self):
        form = self.form(message='a' * 799 + '\r\n' + 'b' * 800)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.cleaned_data['message']), 1600)


@TEXTBEE
class SendSMSServiceTests(TestCase):
    def test_valid_send_returns_batch_id(self):
        with mock.patch(POST, return_value=SEND_OK) as post:
            result = send_sms('+639171234567', 'Hello')

        self.assertTrue(result.success)
        self.assertEqual(result.message_id, 'batch123')
        self.assertEqual(result.status, 'pending')
        kwargs = post.call_args.kwargs
        self.assertEqual(post.call_args.args[0], 'https://api.textbee.dev/api/v1/gateway/send-sms')
        self.assertEqual(kwargs['json'], {'recipients': ['+639171234567'], 'message': 'Hello', 'deviceId': FAKE_DEVICE})
        self.assertEqual(kwargs['headers']['x-api-key'], FAKE_KEY)
        self.assertEqual(kwargs['timeout'], REQUEST_TIMEOUT)

    @override_settings(TEXTBEE_SIM_SLOT='1')
    def test_sim_slot_is_sent_when_configured(self):
        with mock.patch(POST, return_value=SEND_OK) as post:
            send_sms('+639171234567', 'Hello')
        self.assertEqual(post.call_args.kwargs['json']['simSlotIndex'], 1)

    @override_settings(TEXTBEE_API_KEY='', TEXTBEE_DEVICE_ID='')
    def test_missing_credentials_are_handled_before_calling_textbee(self):
        with mock.patch(POST) as post:
            result = send_sms('+639171234567', 'Hello')
        post.assert_not_called()
        self.assertFalse(result.success)
        self.assertEqual(result.status, 'not_submitted')
        self.assertIn('not configured', result.error)

    def assert_send_fails(self, response=None, side_effect=None, expected_text=''):
        with mock.patch(POST, return_value=response, side_effect=side_effect):
            with self.assertLogs('sms_app', level='WARNING') as logs:
                result = send_sms('+639171234567', 'Hello')
        self.assertFalse(result.success)
        self.assertEqual(result.status, 'not_submitted')
        self.assertIn(expected_text, result.error)
        self.assertNotIn(FAKE_KEY, result.error)
        self.assertNotIn(FAKE_KEY, '\n'.join(logs.output))
        return result

    def test_invalid_api_key_401(self):
        self.assert_send_fails(fake_response(401, {'error': 'Unauthorized', 'code': 'AUTH_INVALID'}),
                               expected_text='rejected the API key')

    def test_no_enabled_device_400(self):
        result = self.assert_send_fails(fake_response(400, {'message': 'No enabled device found'}),
                                        expected_text='No enabled device found')
        self.assertIn('textbee app is running', result.error)

    def test_plan_limit_429(self):
        self.assert_send_fails(fake_response(429, {'message': 'Daily limit exceeded'}),
                               expected_text='plan limit has been reached')

    def test_network_connection_error(self):
        self.assert_send_fails(side_effect=requests.ConnectionError(), expected_text='Could not connect to textbee')

    def test_network_timeout(self):
        self.assert_send_fails(side_effect=requests.Timeout(), expected_text='did not respond in time')

    def test_non_json_server_error(self):
        self.assert_send_fails(fake_response(500, json_error=True), expected_text='HTTP 500')


@TEXTBEE
class StatusServiceTests(TestCase):
    def test_status_refresh_returns_delivered(self):
        with mock.patch(GET, return_value=batch_status('delivered')) as get:
            result = get_sms_status('batch123')
        self.assertTrue(result.success)
        self.assertEqual(result.status, 'delivered')
        self.assertTrue(get.call_args.args[0].endswith(f'/gateway/devices/{FAKE_DEVICE}/sms-batch/batch123'))

    def test_failed_status_includes_textbee_reason(self):
        with mock.patch(GET, return_value=batch_status('failed', errorMessage='No SMS credit on SIM.')):
            result = get_sms_status('batch123')
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.error, 'No SMS credit on SIM.')

    def test_unknown_status_is_not_saved(self):
        with mock.patch(GET, return_value=batch_status('something-new')):
            with self.assertLogs('sms_app', level='WARNING'):
                result = get_sms_status('batch123')
        self.assertFalse(result.success)


@TEXTBEE
class SendViewTests(TestCase):
    url = reverse('sms_app:send_sms')

    def post(self, recipient='09171234567', message='Hello'):
        return self.client.post(self.url, {'recipient': recipient, 'message': message}, follow=True)

    def alert_texts(self, response):
        """The feedback messages shown on the final page."""
        return [str(m) for m in response.context['messages']]

    def test_form_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, 'Send SMS')

    def test_valid_send_saves_record_with_batch_id(self):
        with mock.patch(POST, return_value=SEND_OK):
            response = self.post()

        sms = SMSMessage.objects.get()
        self.assertEqual(sms.recipient, '+639171234567')
        self.assertEqual(sms.provider, 'textbee')
        self.assertEqual(sms.provider_message_id, 'batch123')
        self.assertEqual(sms.status, 'pending')
        self.assertContains(response, 'submitted to textbee (status: pending)')

    def test_success_message_does_not_claim_delivery(self):
        with mock.patch(POST, return_value=SEND_OK):
            response = self.post()
        [alert] = self.alert_texts(response)
        self.assertIn('submitted to textbee', alert)
        self.assertNotIn('delivered', alert.lower())

    def test_invalid_input_does_not_call_textbee_or_save(self):
        with mock.patch(POST) as post:
            response = self.post(recipient='abc', message='')
        post.assert_not_called()
        self.assertEqual(SMSMessage.objects.count(), 0)
        self.assertContains(response, 'Enter a valid phone number')
        self.assertContains(response, 'Please enter a message.')

    def test_provider_failure_is_saved_and_shown(self):
        with mock.patch(POST, return_value=fake_response(401, {'error': 'Unauthorized'})):
            with self.assertLogs('sms_app', level='WARNING'):
                response = self.post(message='Keep my text')

        sms = SMSMessage.objects.get()
        self.assertEqual(sms.status, 'not_submitted')
        self.assertEqual(sms.provider_message_id, '')
        self.assertContains(response, 'The message was not sent.')
        self.assertContains(response, 'Keep my text')  # input kept so the user can retry
        self.assertNotContains(response, FAKE_KEY)

    @override_settings(TEXTBEE_API_KEY='', TEXTBEE_DEVICE_ID='')
    def test_missing_credentials_shows_error_without_crashing(self):
        with mock.patch(POST) as post:
            with self.assertLogs('sms_app', level='ERROR'):
                response = self.post()
        post.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The SMS service is not configured.')

    def test_csrf_token_is_required(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(self.url, {'recipient': '09171234567', 'message': 'Hello'})
        self.assertEqual(response.status_code, 403)


@TEXTBEE
class HistoryViewTests(TestCase):
    def setUp(self):
        self.sent = SMSMessage.objects.create(recipient='+639171234567', body='Hi',
                                              provider_message_id='batch123', status='pending')
        self.not_sent = SMSMessage.objects.create(recipient='+639171234567', body='Hi', status='not_submitted',
                                                  error_message='Could not connect to textbee.')

    def test_history_shows_counts_and_badges(self):
        response = self.client.get(reverse('sms_app:history'))
        self.assertEqual(response.context['counts'], {'total': 2, 'submitted': 1, 'failed': 1})
        self.assertContains(response, 'text-bg-secondary')  # pending badge
        self.assertContains(response, 'Could not connect to textbee.')

    def test_refresh_saves_delivered_status(self):
        with mock.patch(GET, return_value=batch_status('delivered')):
            response = self.client.post(reverse('sms_app:refresh_status', args=[self.sent.pk]), follow=True)
        self.sent.refresh_from_db()
        self.assertEqual(self.sent.status, 'delivered')
        self.assertContains(response, 'is now &quot;Delivered&quot;')

    def test_refresh_saves_failure_reason(self):
        with mock.patch(GET, return_value=batch_status('failed', errorMessage='No SMS credit on SIM.')):
            self.client.post(reverse('sms_app:refresh_status', args=[self.sent.pk]))
        self.sent.refresh_from_db()
        self.assertEqual(self.sent.status, 'failed')
        self.assertEqual(self.sent.error_message, 'No SMS credit on SIM.')

    def test_refresh_of_unsubmitted_message_does_not_call_textbee(self):
        with mock.patch(GET) as get:
            response = self.client.post(reverse('sms_app:refresh_status', args=[self.not_sent.pk]), follow=True)
        get.assert_not_called()
        self.assertContains(response, 'never submitted to textbee')

    def test_refresh_requires_post(self):
        response = self.client.get(reverse('sms_app:refresh_status', args=[self.sent.pk]))
        self.assertEqual(response.status_code, 405)
