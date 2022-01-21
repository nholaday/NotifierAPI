import os
from datetime import datetime
from django.http import Http404
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.response import Response
from notifier.models import UserPreference
from notifier.serializers import UserPrefSerializer, NotificationSerializer
from notifier.tasks import trigger_email_task, trigger_sms_task
from drf_spectacular.utils import extend_schema


@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'preference': reverse('preference', request=request, format=format),
        'notify': reverse('notify', request=request, format=format),
        'OpenAPI formatted documentation': reverse('swagger-ui', request=request, format=format),
        'ReDoc formatted documentation': reverse('redoc', request=request, format=format),
    })

class UserPrefDetail(APIView):
    """Show or edit User Preference info for logged in user"""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    # TODO: account for case that no user is logged in
    def get_object(self, request):
        try:
            return UserPreference.objects.get(user=self.request.user)
        except UserPreference.DoesNotExist:
            # if the user doesn't have a preference set up, create a blank one
            preference = UserPreference(user=self.request.user)
            preference.save()
            return preference

    @extend_schema(request=UserPrefSerializer, responses=UserPrefSerializer)
    def get(self, request, format=None):
        preference = self.get_object(request)
        serializer = UserPrefSerializer(preference)
        return Response(serializer.data)

    @extend_schema(request=UserPrefSerializer, responses=UserPrefSerializer)
    def post(self, request, format=None):
        preference = self.get_object(request)
        serializer = UserPrefSerializer(preference, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class SendNotification(UserPrefDetail):
    """Sends a email or sms notification using user's preference"""

    def send_email(self, preference, serializer):
        """Send an email using SendGrid API with user email and reqeust data"""
        # User is allowed to have a blank email, so check for an email first
        # if it is not blank, it will be validated by the serializer
        if not preference.user.email:
            msg = (
                "No email stored for this user. "
                "Use POST /preference/ endpoint to set email"
            )
            return Response([msg], status=status.HTTP_400_BAD_REQUEST)
        result = trigger_email_task.apply_async(
            (preference.user.email, serializer.data),
            eta = serializer.data.get('sendtime', datetime.utcnow()),
        )
        respdata = serializer.data
        respdata['email'] = preference.user.email
        return Response(respdata)

    def send_sms(self, preference, serializer):
        """Trigger sending an sms using celery"""
        # Since we are scheduling sms messages to be sent in the future,
        # we need to validate the phone number before scheduling the task
        # TODO: validate phone number using Twilio API
        # kwargs = {"eta": serializer.data.sendtime}
        if preference.phone is None:
            msg = (
                "No phone number stored for this user. "
                "Use POST /preference/ endpoint to set phone"
            )
            return Response([msg], status=status.HTTP_400_BAD_REQUEST)

        result = trigger_sms_task.apply_async(
            (preference.phone, serializer.data),
            eta = serializer.data.get('sendtime', datetime.utcnow()),
        )
        respdata = serializer.data
        respdata['phone'] = preference.phone
        return Response(respdata)

    @extend_schema(request=NotificationSerializer, responses=NotificationSerializer)
    def post(self, request, format=None):
        preference = self.get_object(request)
        serializer = NotificationSerializer(data=request.data)

        if serializer.is_valid():
            if preference.notify_pref == "None":
                msg = (
                    "Notification preference is saved as 'None' for this user."
                    "Use POST /preference/ endpoint to set a preference to email or sms"
                )
                return Response([msg])
            elif preference.notify_pref == 'email':
                return self.send_email(preference, serializer)
            else:
                return self.send_sms(preference, serializer)
                # We won't know if the request worked since it is scheduled to be sent
                # in the future with celery.  So simply return that it was a response if
                # it was with the sms, title, text, and sendtime it is scheduled for

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
