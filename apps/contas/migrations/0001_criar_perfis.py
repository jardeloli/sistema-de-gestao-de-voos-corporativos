from django.db import migrations

PERFIS = ["Administrador", "Gestor", "Agendador", "Operacional"]


def criar(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nome in PERFIS:
        Group.objects.get_or_create(name=nome)


def remover(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=PERFIS).delete()


class Migration(migrations.Migration):
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(criar, remover)]
