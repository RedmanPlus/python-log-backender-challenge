import structlog
from django.db.models import QuerySet
from result import Err, Ok, Result

from core.event_log_client import EventLogClient
from users.dtos.user import UserCreated
from users.models import User, UserCreatedMessage, UserCreatedMessageStatus

logger = structlog.get_logger(__name__)

def create_user(email: str, first_name: str, last_name: str) -> Result[User, str]:
    user, created = User.objects.get_or_create(
        email=email,
        first_name=first_name,
        last_name=last_name,
    )

    if created:
        return Ok(user)
    return Err("User with this email already exists")

def create_user_created_message(user: User) -> UserCreatedMessage:
    return UserCreatedMessage.objects.create(
        user=user,
    )

def send_user_created_message_batch(
    messages: QuerySet[UserCreatedMessage],
    client: EventLogClient,
) -> None:
    """Sends a batch of user created messages to the event log.
    
    Must be called with messages already filtered for `PENDING` or 'FAILED'
    statuses and inside of a EventLogClient context manager.

    Parameters:
        messages: QuerySet[UserCreatedMessage]
            A queryset of UserCreatedMessage objects to send to the event log.
        client: Client
            An EventLogClient instance.
    """
    user_created_messages = [
        UserCreated(
            email=msg.user.email,
            first_name=msg.user.first_name or '',
            last_name=msg.user.last_name or '',
        )
        for msg in messages
    ]

    res = client.insert(data=user_created_messages)
    match res:
        case Ok():
            logger.info("UserCreated message batch successfully sent")
            messages.update(status=UserCreatedMessageStatus.SENT)
        case Err(msg):
            logger.error(f"UserCreated message batch failed to be sent: {msg}")
            messages.update(status=UserCreatedMessageStatus.FAILED)
