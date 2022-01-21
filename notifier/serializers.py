from rest_framework import serializers
from notifier.models import UserPreference


class UserPrefSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.EmailField(source='user.email', required=False)
    
    # custom update method necessary to change email on 
    # both User model and UserPreference model
    def update(self, instance, validated_data):
        """Update and return preference and email"""
        instance.user.email = validated_data.get('user', {'email':""}).get(
            'email', instance.user.email
        )
        instance.notify_pref = validated_data.get('notify_pref', instance.notify_pref)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.user.save()
        instance.save()
        return instance

    class Meta:
        model = UserPreference
        fields = ['username', 'notify_pref', 'email', 'phone']

# Don't need a model for Notifications since the data isn't saved in the db
class NotificationSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=254, allow_blank=True, required=False)
    text = serializers.CharField(allow_blank=False, required=True)
    # input should be ISO 8601 formatted datetime e.g. "2021-09-06T15:47:30-07:00"
    sendtime = serializers.DateTimeField(required=False)