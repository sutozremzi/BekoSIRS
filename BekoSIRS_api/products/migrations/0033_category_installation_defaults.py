# Generated manually — seed installation metadata for all known categories.
# requires_installation + install_duration_min per category so the delivery
# planner can compute realistic daily time budgets.

from django.db import migrations


# (name_fragment, requires_installation, install_duration_min)
# name_fragment is matched case-insensitively via __icontains so partial names
# are fine. Order matters: more specific rules run first.
CATEGORY_RULES = [
    # ── Klimalar — teknik ekip montajı, en uzun süre ──────────────────
    ("klima",                       True,  45),

    # ── Ankastre (gömme) ürünler — mutfak içine montaj ───────────────
    ("ankastre bulaşık",            True,  35),
    ("ankastre fırın",              True,  35),
    ("ankastre mikrodalga",         True,  35),
    ("ankastre ocak",               True,  35),
    ("sürgülü",                     True,  35),   # sürgülü aspiratör
    ("gömme aspiratör",             True,  35),

    # ── Davlumbaz / aspiratör (asma montaj) ──────────────────────────
    ("davlumbaz",                   True,  25),
    ("aspiratör",                   True,  25),

    # ── Çamaşır & kurutma — su bağlantısı ────────────────────────────
    ("çamaşır",                     True,  30),
    ("kurutma",                     True,  30),

    # ── Bulaşık makinesi (tezgah altı) ───────────────────────────────
    ("bulaşık makinesi",            True,  30),

    # ── Buzdolabı & dondurucu — taşıma + yerleştirme ─────────────────
    ("buzdolabı",                   True,  20),
    ("neo frost",                   True,  20),
    ("dondurucu",                   True,  20),

    # ── Su sebili — su bağlantısı + test ─────────────────────────────
    ("su sebili",                   True,  25),

    # ── TV'ler — askı + kablo ─────────────────────────────────────────
    ("tv",                          True,  15),
    ("televizyon",                  True,  15),

    # ── Solo fırın (tezgah üzeri / serbest duran) ────────────────────
    ("solo fırın",                  True,  20),

    # ── Tak-çalıştır / taşınabilir — kurulum yok ─────────────────────
    ("gıda hazırlama",              False,  0),
    ("pişirici",                    False,  0),
    ("ısıtıcı",                     False,  0),
    ("içecek",                      False,  0),
    ("süpürge",                     False,  0),
    ("tezgah üzeri",                False,  0),
    ("mikrodalga",                  False,  0),   # solo/tezgah üzeri kalanlar
]


def apply_category_rules(apps, schema_editor):
    Category = apps.get_model("products", "Category")
    all_cats = list(Category.objects.all())

    for cat in all_cats:
        name_lower = cat.name.lower()
        matched = False
        for fragment, requires, duration in CATEGORY_RULES:
            if fragment.lower() in name_lower:
                cat.requires_installation = requires
                cat.install_duration_min = duration
                matched = True
                break
        if not matched:
            # Safe default: no installation
            cat.requires_installation = False
            cat.install_duration_min = 0
        cat.save(update_fields=["requires_installation", "install_duration_min"])


def reverse_category_rules(apps, schema_editor):
    Category = apps.get_model("products", "Category")
    Category.objects.update(requires_installation=False, install_duration_min=0)


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0032_category_install_duration_min_and_more"),
    ]

    operations = [
        migrations.RunPython(apply_category_rules, reverse_category_rules),
    ]
