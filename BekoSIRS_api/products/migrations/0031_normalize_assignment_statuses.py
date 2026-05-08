from django.db import migrations


def normalize_assignment_statuses(apps, schema_editor):
    ProductAssignment = apps.get_model('products', 'ProductAssignment')
    ProductAssignment.objects.filter(status='PENDING').update(status='PLANNED')
    ProductAssignment.objects.filter(status='delivered').update(status='DELIVERED')


def reverse_normalize_assignment_statuses(apps, schema_editor):
    # Keep the normalized values on rollback; old mixed-case values were invalid.
    pass


class Migration(migrations.Migration):

    dependencies = [
        # Bu data migration mantik olarak 0029'a bagliydi, ancak ayni numarada
        # baska bir migration (0030_add_user_category_preference) main'e merge
        # edildigi icin 0031'e tasindi ve dependency'si o leaf'e cekildi;
        # boylece Django migration grafinde tek leaf node kalir, "multiple
        # leaf nodes" hatasi alinmaz.
        ('products', '0030_add_user_category_preference'),
    ]

    operations = [
        migrations.RunPython(normalize_assignment_statuses, reverse_normalize_assignment_statuses),
    ]
