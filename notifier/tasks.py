from celery import shared_task
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client 
from twilio.base.exceptions import TwilioRestException


@shared_task
def trigger_email_task(email, serializer_data):
    message = Mail(
        from_email=settings.SENDGRID_FROM_EMAIL,
        to_emails=email,
        subject=serializer_data.get('title', ''),
        html_content=serializer_data.get('text', ''),
    )
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    response = sg.send(message)
    return response.status_code

@shared_task
def trigger_sms_task(phone, serializer_data):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH) 
        
    try:
        message = client.messages.create(  
            # since there is no title for a sms, 
            # simply separate title and text with a new line
            body="\n".join([
                serializer_data.get('title', ''),
                serializer_data.get('text', ''),
            ]),
            to='+' + str(phone),
            # defines where the message is coming from
            messaging_service_sid=settings.TWILIO_MESSAGING_SERVICE_SID
        ) 
    except TwilioRestException as e:
        return [e.msg, status.HTTP_400_BAD_REQUEST]
    return message.status

