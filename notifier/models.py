from django.db import models
from django.contrib.auth.models import User


class UserPreference(models.Model):
    PREFERENCE_CHOICES = [
        ('email', 'email'),
        ('sms', 'SMS'),
        ('None', 'None'),
    ]

    user = models.OneToOneField(
        User, 
        related_name='userpreference', 
        on_delete=models.CASCADE,
    )
    notify_pref = models.CharField(
        choices=PREFERENCE_CHOICES, 
        default='email', 
        max_length=100
    )
    # requires custom validation?
    phone = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return self.user.username