# Generated by Django 4.0.6 on 2022-07-31 17:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='user_type',
            field=models.IntegerField(choices=[(0, 'مدیر'), (1, 'کاربر')], default=0),
        ),
    ]
