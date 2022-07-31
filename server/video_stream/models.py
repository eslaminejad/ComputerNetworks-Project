from django.db import models

# Create your models here.
from users.models import User


class Video(models.Model):
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
