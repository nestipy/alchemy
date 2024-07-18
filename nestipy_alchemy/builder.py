from dataclasses import dataclass
from typing import Union, Type

from nestipy.dynamic_module import ConfigurableModuleBuilder
from sqlalchemy import URL
from sqlalchemy.orm import DeclarativeBase


@dataclass
class SQLAlchemyOption:
    url: Union[str, URL]
    declarative_base: Type[DeclarativeBase]
    echo: bool = False
    sync: bool = False


ConfigurableModuleClass, SQLALCHEMY_OPTION = ConfigurableModuleBuilder[SQLAlchemyOption]().set_method(
    'for_root_app').build()
