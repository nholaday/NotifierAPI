import json

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from notifier.models import UserPreference
from notifier.views import api_root
from notifier.tasks import trigger_email_task, trigger_sms_task


class PreferenceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(
            username="testuser",
            password="testpass"
        )
        User.objects.create(
            username="testuser2",
            password="testpass2"
        )
        self.client.force_authenticate(user=self.user)

    def test_api_root(self):
        response = self.client.get("/")
        expected_data = {
            "preference": "http://testserver/preference/",
            "notify": "http://testserver/notify/"
        }
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)
    
    def test_preference_get(self):
        """Should only see the data of the logged in user"""

        response = self.client.get(reverse('preference'))
        expected_data = {
            "username": "testuser",
            "notify_pref": "email",
            "email": "",
            "phone": None
        }
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)
        preference = UserPreference.objects.filter(user=self.user)
        # ensure a UserPreference object was created
        self.assertEqual(len(preference), 1)
        preference = preference[0]
        self.assertEqual(preference.notify_pref, "email")
        self.assertEqual(preference.user.email, "")
        self.assertIsNone(preference.phone)
        

    def test_preference_post(self):
        # Test preference POST changing notify_pref, email, phone
        # Test with no data, nothing should change
        response = self.client.post(reverse('preference'))
        preference = UserPreference.objects.get(user=self.user)

        expected_data = {
            "username": "testuser",
            "notify_pref": "email",
            "email": "",
            "phone": None
        }
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)
        self.assertEqual(preference.notify_pref, "email")
        self.assertEqual(preference.user.email, "")
        self.assertIsNone(preference.phone)
    
    def test_changing_notify_pref(self):    
        # Test changing notify_pref
        body = {"notify_pref": "sms"}
        response = self.client.post(reverse('preference'), body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        preference = UserPreference.objects.get(user=self.user)
        self.assertEqual(preference.notify_pref, "sms")

        body = {"notify_pref": "None"}
        response = self.client.post(reverse('preference'), body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        preference = UserPreference.objects.get(user=self.user)
        self.assertEqual(preference.notify_pref, "None")

        body = {"notify_pref": "not_a_choice"}
        response = self.client.post(reverse('preference'), body)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        preference = UserPreference.objects.get(user=self.user)
        self.assertEqual(preference.notify_pref, "None")
        
    def test_changing_email(self):
        # Test changing email
        body = {"email": "a@a.com"}
        response = self.client.post(reverse('preference'), body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        preference = UserPreference.objects.get(user=self.user)
        self.assertEqual(preference.user.email, "a@a.com")

        body = {"email": "invalid email address"}
        response = self.client.post(reverse('preference'), body)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        preference = UserPreference.objects.get(user=self.user)
        self.assertEqual(preference.user.email, "a@a.com")

    def test_changing_phone(self):
        # Test changing phone
        body = {"phone": "123456789"}
        response = self.client.post(reverse('preference'), body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        preference = UserPreference.objects.get(user=self.user)
        self.assertEqual(preference.phone, 123456789)

        body = {"phone": "invalid phone number"}
        response = self.client.post(reverse('preference'), body)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        preference = UserPreference.objects.get(user=self.user)
        self.assertEqual(preference.phone, 123456789)
        
    def test_changing_all_preferences(self):
        # Test changing all at once
        body = {
            "notify_pref": "email",
            "email": "b@b.com",
            "phone": 987654321
        }
        response = self.client.post(reverse('preference'), body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        preference = UserPreference.objects.get(user=self.user)
        self.assertEqual(preference.notify_pref, "email")
        self.assertEqual(preference.user.email, "b@b.com")
        self.assertEqual(preference.phone, 987654321)
        
    
class NotifyTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create(
            username="testuser",
            password="testpass"
        )
        User.objects.create(
            username="testuser2",
            password="testpass2"
        )
        self.client.force_authenticate(user=self.user)
        self.serializer_data = {
            "title": "Subject text example",
            "text": "Body text example",
            "sendtime": "2021-09-06T15:52:10-07:00"
        }

    def test_notify_get(self):
        response = self.client.get(reverse('notify'))
        expected_data = {
            "username": "testuser",
            "notify_pref": "email",
            "email": "",
            "phone": None
        }
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)
        preference = UserPreference.objects.filter(user=self.user)
        # ensure a UserPreference object was created
        self.assertEqual(len(preference), 1)
        preference = preference[0]
        self.assertEqual(preference.notify_pref, "email")
        self.assertEqual(preference.user.email, "")
        self.assertIsNone(preference.phone)
    
    def test_notify_post_no_body(self):
        # Test failed request with no body, text field required
        response = self.client.post(reverse('notify'))
        expected_data = "[ErrorDetail(string='This field is required.', code='required')]"
        self.assertEqual(str(response.data['text']), expected_data)

    def test_notify_email(self):
        # Test notify_pref==email with blank email
        response = self.client.post(reverse('notify'), self.serializer_data)
        preference = UserPreference.objects.get(user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test notify_pref==email with valid email
        body = {"email": "a@a.com"}
        response = self.client.post(reverse('preference'), body)
        response = self.client.post(reverse('notify'), self.serializer_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_trigger_email_task(self):
        # Because the task is sent to celery to be executed we can't be sure if
        # it was successful or not.
        # test trigger_email_task without sending to celery
        
        # initialize the user preference first
        self.test_notify_email()
        
        preference = UserPreference.objects.get(user=self.user)
        result = trigger_email_task(preference.user.email, self.serializer_data)
        self.assertEqual(result, status.HTTP_202_ACCEPTED)
        
        # Test with an invalid email
        with self.assertRaises(KeyError):
            result = trigger_email_task("invalidemail", self.serializer_data)
        
    def test_notify_sms(self):
        # Test notify_pref==sms with phone=None
        body = {"notify_pref": "sms"}
        response = self.client.post(reverse('preference'), body)
        response = self.client.post(reverse('notify'), self.serializer_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test notify_pref==sms with valid phone number
        body = {"phone": "1234567890"}
        response = self.client.post(reverse('preference'), body)
        response = self.client.post(reverse('notify'), self.serializer_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_trigger_sms_task(self):
        # test trigger_sms_task without sending to celery
        
        # initialize the user preference first
        self.test_notify_sms()

        preference = UserPreference.objects.get(user=self.user)
        result = trigger_sms_task(preference.phone, self.serializer_data)
        self.assertEqual(result[1], status.HTTP_400_BAD_REQUEST)
    
    def test_notify_none(self):
        # Test notify_pref==sms with phone=None
        body = {"notify_pref": "None"}
        response = self.client.post(reverse('preference'), body)
        msg = (
            "Notification preference is saved as 'None' for this user."
            "Use POST /preference/ endpoint to set a preference to email or sms"
        )
        response = self.client.post(reverse('notify'), self.serializer_data)
        self.assertEqual(response.data, [msg])


