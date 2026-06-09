from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('detector', '0002_alter_vehiclelog_detected_time_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiclelog',
            name='object_id',
            field=models.IntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name='vehiclelog',
            name='confidence',
            field=models.FloatField(default=0.0),
        ),
        migrations.AlterField(
            model_name='vehiclelog',
            name='direction',
            field=models.CharField(max_length=10),
        ),
        migrations.AddIndex(
            model_name='vehiclelog',
            index=models.Index(
                fields=['vehicle_type', 'direction'],
                name='detector_ve_vehicle_dir_idx',
            ),
        ),
    ]
