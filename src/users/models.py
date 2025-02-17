from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.db.models.enums import TextChoices

from core.models import TimeStampedModel


class User(TimeStampedModel, AbstractBaseUser):
    email = models.EmailField(unique=True, db_index=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'

    class Meta(AbstractBaseUser.Meta):
        app_label = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self) -> str:
        if all([self.first_name, self.last_name]):
            return f'{self.first_name} {self.last_name}'

        return self.email


class UserCreatedMessageStatus(TextChoices):
    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'


class UserCreatedMessage(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=255,
        choices=UserCreatedMessageStatus.choices,
        default=UserCreatedMessageStatus.PENDING,
    )

    class Meta:
        verbose_name = 'User Created Message'
        verbose_name_plural = 'User Created Messages'

    def __str__(self) -> str:
        return f'{self.user.email} - {self.status}'
