from typing import Any

import structlog
from result import Err, Ok

from core.use_case import UseCase
from users.dtos.user import CreateUserRequest, CreateUserResponse
from users.services.user import create_user, create_user_created_message

logger = structlog.get_logger(__name__)


class CreateUser(UseCase):
    def _get_context_vars(self, request: CreateUserRequest) -> dict[str, Any]:
        return {
            'email': request.email,
            'first_name': request.first_name,
            'last_name': request.last_name,
        }

    def _execute(self, request: CreateUserRequest) -> CreateUserResponse:
        logger.info('creating a new user')

        user_result = create_user(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
        )

        match user_result:
            case Ok(user):
                logger.info('user has been created')
                create_user_created_message(user=user)
                return CreateUserResponse(result=user)
            case Err(msg):
                logger.error('unable to create a new user')
                return CreateUserResponse(error=msg)

