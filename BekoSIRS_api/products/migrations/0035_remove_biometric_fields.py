from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0034_fix_category_installation_missed'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='biometric_enabled',
        ),
        migrations.RemoveField(
            model_name='customuser',
            name='face_encoding',
        ),
    ]
