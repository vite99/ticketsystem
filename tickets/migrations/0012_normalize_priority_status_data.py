from django.db import migrations


PRIORITY_RULES = {
    "low": {
        "aliases": {"low", "Низкий", "РќРёР·РєРёР№"},
        "color": "#17a2b8",
    },
    "medium": {
        "aliases": {"medium", "Средний", "РЎСЂРµРґРЅРёР№"},
        "color": "#ffc107",
    },
    "high": {
        "aliases": {"high", "Высокий", "Р’С‹СЃРѕРєРёР№"},
        "color": "#fd7e14",
    },
    "critical": {
        "aliases": {"critical", "Критический", "РљСЂРёС‚РёС‡РµСЃРєРёР№"},
        "color": "#dc3545",
    },
}

STATUS_RULES = {
    "open": {
        "aliases": {"open", "Открыт", "РћС‚РєСЂС‹С‚"},
        "color": "#0d6efd",
        "is_final": False,
    },
    "in_progress": {
        "aliases": {"in_progress", "В работе", "Р’ СЂР°Р±РѕС‚Рµ"},
        "color": "#6f42c1",
        "is_final": False,
    },
    "waiting": {
        "aliases": {"waiting", "Ожидание", "РћР¶РёРґР°РЅРёРµ"},
        "color": "#ffc107",
        "is_final": False,
    },
    "resolved": {
        "aliases": {"resolved", "Решен", "РРµС€РµРЅ", "Р\xa0РµС€РµРЅ"},
        "color": "#198754",
        "is_final": False,
    },
    "closed": {
        "aliases": {"closed", "Закрыт", "Р—Р°РєСЂС‹С‚"},
        "color": "#6c757d",
        "is_final": True,
    },
    "reopened": {
        "aliases": {"reopened", "Переоткрыт", "РџРµСЂРµРѕС‚РєСЂС‹С‚"},
        "color": "#dc3545",
        "is_final": False,
    },
}


def _normalize_model(apps, model_name, fk_field_name, rules):
    model = apps.get_model("tickets", model_name)
    ticket_model = apps.get_model("tickets", "Ticket")

    for target_name, rule in rules.items():
        aliases = rule["aliases"]
        objects = list(model.objects.filter(name__in=aliases).order_by("id"))

        if not objects:
            canonical = model.objects.create(
                name=target_name,
                **{k: v for k, v in rule.items() if k != "aliases"},
            )
            objects = [canonical]

        canonical = next((obj for obj in objects if obj.name == target_name), objects[0])

        updates = {k: v for k, v in rule.items() if k != "aliases"}
        updates["name"] = target_name
        for field_name, value in updates.items():
            setattr(canonical, field_name, value)
        canonical.save()

        duplicates = [obj for obj in objects if obj.pk != canonical.pk]
        if duplicates:
            ticket_model.objects.filter(**{f"{fk_field_name}__in": duplicates}).update(**{fk_field_name: canonical})
            model.objects.filter(pk__in=[obj.pk for obj in duplicates]).delete()


def normalize_priority_status_data(apps, schema_editor):
    _normalize_model(apps, "Priority", "priority", PRIORITY_RULES)
    _normalize_model(apps, "Status", "status", STATUS_RULES)


class Migration(migrations.Migration):

    dependencies = [
        ("tickets", "0011_alter_priority_options_alter_status_options_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_priority_status_data, migrations.RunPython.noop),
    ]
