import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0064_bestellung_lieferdatum_bestellung_lieferschein'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bestellung',
            name='standort',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='bestellungen',
                to='devices.standort',
                verbose_name='Standort'
            ),
        ),
    ]