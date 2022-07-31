from django.contrib.auth.models import AbstractUser
from django.db import models


class UserType(models.IntegerChoices):
    """
    A class used to represent user types in system (admin, customer, carpet_cleaning_owner)
    """

    admin = 0, "مدیر"
    user = 1, "کاربر"


class User(AbstractUser):
    """
    A class used for representing different users in system

    Parameters
    -------
    user_type: UserType
    """

    user_type = models.IntegerField(
        blank=False, choices=UserType.choices, default=UserType.admin
    )

    def __eq__(self, other):
        if other:
            return self.username == other.username
        return False
