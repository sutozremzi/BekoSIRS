# Fix two categories missed in 0033 due to Turkish plural/vowel-harmony forms:
#   "Bulaşık Makineleri"   — fragment "bulaşık makinesi" didn't match (çoğul)
#   "Tek ve Çift Kapılı Statik Buzdolapları" — "buzdolabı" didn't match (ses uyumu)

from django.db import migrations

FIXES = [
    # (name_fragment_stem, requires_installation, install_duration_min)
    ("bulaşık makine",  True, 30),   # bağımsız tezgah altı bulaşık makinesi
    ("buzdolap",        True, 20),   # statik buzdolapları dahil
]


def apply_fixes(apps, schema_editor):
    Category = apps.get_model("products", "Category")
    for fragment, requires, duration in FIXES:
        qs = Category.objects.filter(name__icontains=fragment)
        qs.update(requires_installation=requires, install_duration_min=duration)


def reverse_fixes(apps, schema_editor):
    Category = apps.get_model("products", "Category")
    for fragment, _, _ in FIXES:
        qs = Category.objects.filter(name__icontains=fragment)
        qs.update(requires_installation=False, install_duration_min=0)


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0033_category_installation_defaults"),
    ]

    operations = [
        migrations.RunPython(apply_fixes, reverse_fixes),
    ]
