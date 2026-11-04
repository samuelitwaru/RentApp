from django.db import migrations

from expenses.models import DEFAULT_CATEGORIES


def seed_categories(apps, schema_editor):
    ExpenseCategory = apps.get_model("expenses", "ExpenseCategory")
    for name, description in DEFAULT_CATEGORIES:
        ExpenseCategory.objects.get_or_create(name=name, defaults={"description": description})


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, noop_reverse),
    ]
