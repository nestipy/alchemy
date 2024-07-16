from typing import Annotated

from nestipy.common import Module
from nestipy.ioc import Inject
from nestipy_config import ConfigModule, ConfigService

from app_controller import AppController
from app_service import AppService
from nestipy_alchemy import SQLAlchemyModule, SQLAlchemyOption
from user_model import Base


async def sqlalchemy_option(config: Annotated[ConfigService, Inject()]) -> SQLAlchemyOption:
    return SQLAlchemyOption(
        url=config.get("DATABASE_URL"),
        declarative_base=Base,
        sync=False
    )


@Module(
    imports=[
        ConfigModule.for_root(),
        SQLAlchemyModule.for_root_async(
            factory=sqlalchemy_option,
            inject=[ConfigService],
            imports=[ConfigModule],
        )
    ],
    controllers=[AppController],
    providers=[AppService]
)
class AppModule:
    ...
