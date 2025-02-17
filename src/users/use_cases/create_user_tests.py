import uuid
from collections.abc import Generator
from time import sleep

import pytest
from clickhouse_connect.driver.client import Client
from django.conf import settings

from users.dtos.user import CreateUserRequest
from users.models import UserCreatedMessage, UserCreatedMessageStatus
from users.tasks import check_user_message_buffer
from users.use_cases import CreateUser

pytestmark = [pytest.mark.django_db]


@pytest.fixture()
def f_use_case() -> CreateUser:
    return CreateUser()


@pytest.fixture(autouse=True)
def f_clean_up_event_log(f_ch_client: Client) -> Generator:
    f_ch_client.query(f'TRUNCATE TABLE {settings.CLICKHOUSE_EVENT_LOG_TABLE_NAME}')
    yield


def test_user_created(f_use_case: CreateUser) -> None:
    request = CreateUserRequest(
        email='test@email.com', first_name='Test', last_name='Testovich',
    )

    response = f_use_case.execute(request)

    assert response.result.email == 'test@email.com'
    assert response.error == ''


def test_emails_are_unique(f_use_case: CreateUser) -> None:
    request = CreateUserRequest(
        email='test@email.com', first_name='Test', last_name='Testovich',
    )

    f_use_case.execute(request)
    response = f_use_case.execute(request)

    assert response.result is None
    assert response.error == 'User with this email already exists'


def test_event_log_entry_published(
    f_use_case: CreateUser,
    f_ch_client: Client,
) -> None:
    email = f'test_{uuid.uuid4()}@email.com'
    request = CreateUserRequest(
        email=email, first_name='Test', last_name='Testovich',
    )

    f_use_case.execute(request)

    message = UserCreatedMessage.objects.filter(user__email=email).first()

    assert message is not None
    assert message.status == UserCreatedMessageStatus.PENDING


@pytest.mark.slow
def test_message_buffer_query_sent(
    f_use_case: CreateUser,
    f_ch_client: Client,
) -> None:
    random_emails = (f"test_{uuid.uuid4()}@email.com" for _ in range(1000))

    num_queries = f_ch_client.query(
        """SELECT query FROM system.query_log
        WHERE (
                type = 'QueryFinish'
                OR type = 'QueryStart'
            )
            AND has(databases, 'default')
            AND has(tables, 'default.event_log')
            AND lower(query) LIKE 'insert%'
        ORDER BY event_time DESC
        """,
    )

    num_queries_pre_test = num_queries.result_rows

    for email in random_emails:
        request = CreateUserRequest(
            email=email,
            first_name="Test",
            last_name="Testovich",
        )

        f_use_case.execute(request=request)

    check_user_message_buffer()

    sleep(6)  # sleeping due to caching issues - otherwise the query below won't show new inserts
    num_queries = f_ch_client.query(
        """SELECT query FROM system.query_log
        WHERE (
                type = 'QueryFinish'
                OR type = 'QueryStart'
            )
            AND has(databases, 'default')
            AND has(tables, 'default.event_log')
            AND lower(query) LIKE 'insert%'
        ORDER BY event_time DESC
        """,
    )

    num_queries_post_test = num_queries.result_rows

    assert len(num_queries_post_test) - len(num_queries_pre_test) == 2

    log = f_ch_client.query("SELECT * FROM default.event_log WHERE event_type = 'user_created'")
    assert len(log.result_rows) == 1000
