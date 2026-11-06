import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0061_alter_bestellung_kategorie_delete_bestellkategorie'),
    ]

    operations = [
        migrations.AddField(
            model_name='bestellung',
            name='standort',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='bestellungen',
                to='devices.standort',
                verbose_name='Standort'
            ),
        ),
        migrations.AlterField(
            model_name='bestellung',
            name='geraet',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='bestellungen',
                to='devices.device',
                verbose_name='Gerät'
            ),
        ),
    ]