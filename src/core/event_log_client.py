import re
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import structlog
from clickhouse_connect import get_client
from clickhouse_connect.driver.client import Client
from clickhouse_connect.driver.exceptions import DatabaseError
from clickhouse_connect.driver.types import Matrix
from django.conf import settings
from django.utils import timezone
from result import Err, Ok, Result

from core.base_model import Model

logger = structlog.get_logger(__name__)

EVENT_LOG_COLUMNS = [
    'event_type',
    'event_date_time',
    'environment',
    'event_context',
]


class EventLogClient:
    def __init__(self, client: Client) -> None:
        self._client = client

    @classmethod
    @contextmanager
    def init(cls) -> Generator['EventLogClient']:
        client = get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            user=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
            query_retries=2,
            connect_timeout=30,
            send_receive_timeout=10,
        )
        try:
            yield cls(client)
        except Exception as e:
            logger.error('error while executing clickhouse query', error=str(e))
        finally:
            client.close()

    def insert(
        self,
        data: list[Model],
    ) -> Result[int, DatabaseError]:
        try:
            summary = self._client.insert(
                data=self._convert_data(data),
                column_names=EVENT_LOG_COLUMNS,
                database=settings.CLICKHOUSE_SCHEMA,
                table=settings.CLICKHOUSE_EVENT_LOG_TABLE_NAME,
            )
            return Ok(summary.written_rows)
        except DatabaseError as e:
            logger.error('unable to insert data to clickhouse', error=str(e))
            return Err(e)

    def query(self, query: str) -> Result[Matrix, DatabaseError]:  # noqa: ANN401
        logger.debug('executing clickhouse query', query=query)

        try:
            return Ok(self._client.query(query).result_rows)
        except DatabaseError as e:
            logger.error('failed to execute clickhouse query', error=str(e))
            return Err(e)

    def _convert_data(self, data: list[Model]) -> list[tuple[Any]]:
        return [
            (
                self._to_snake_case(event.__class__.__name__),
                timezone.now(),
                settings.ENVIRONMENT,
                event.model_dump_json(),
            )
            for event in data
        ]

    def _to_snake_case(self, event_name: str) -> str:
        result = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', event_name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', result).lower()

