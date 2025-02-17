from core.celery import transactioned_task
from core.event_log_client import EventLogClient
from users.selectors.user import get_pending_message_buffer, message_buffer_full
from users.services.user import send_user_created_message_batch


@transactioned_task("check_buffer")
def check_user_message_buffer() -> None:
    buffered_messages = get_pending_message_buffer()
    if message_buffer_full(buffered_messages):
        with EventLogClient.init() as client:
            send_user_created_message_batch(buffered_messages, client)
