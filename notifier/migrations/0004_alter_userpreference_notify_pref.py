# Generated by Django 3.2.7 on 2021-09-07 22:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifier', '0003_alter_userpreference_phone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userpreference',
            name='notify_pref',
            field=models.CharField(choices=[('email', 'email'), ('sms', 'SMS'), ('None', 'None')], default='email', max_length=100),
        ),
    ]
