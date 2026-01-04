# Generated migration for password reset fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0030_customuser_email_verification_sent_at_and_more'),  # Dependency pada migration terakhir
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='password_reset_token',
            field=models.CharField(blank=True, help_text='Token reset password', max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='password_reset_token_created_at',
            field=models.DateTimeField(blank=True, help_text='Waktu token reset password dibuat', null=True),
        ),
    ]
