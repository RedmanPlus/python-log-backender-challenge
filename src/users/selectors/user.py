from django.conf import settings
from django.db.models import QuerySet

from users.models import UserCreatedMessage, UserCreatedMessageStatus


def get_pending_message_buffer() -> QuerySet[UserCreatedMessage]:
    return UserCreatedMessage.objects.filter(
        status__in=[UserCreatedMessageStatus.PENDING, UserCreatedMessageStatus.FAILED],
    ).order_by("status")

def message_buffer_full(messages: QuerySet[UserCreatedMessage]) -> bool:
    buffer_len = messages.count()
    return buffer_len >= settings.MESSAGE_BUFFER_LEN
