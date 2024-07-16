from typing import Union, Type, Callable, Awaitable

from nestipy.common import Module
from nestipy.dynamic_module import DynamicModule

from .builder import SQLAlchemyOption, ConfigurableModuleClass
from .service import SQLAlchemyService


@Module(
    providers=[
        SQLAlchemyService
    ],
    exports=[
        SQLAlchemyService
    ],
    is_global=False
)
class SQLAlchemyModule(ConfigurableModuleClass):

    @classmethod
    def for_root(cls, option: SQLAlchemyOption):
        d_module: DynamicModule = cls.for_root_app(option)
        return d_module

    @classmethod
    def for_root_async(
            cls,
            value: Union[SQLAlchemyOption] = None,
            factory: Callable[..., Union[Awaitable, SQLAlchemyOption]] = None,
            existing: Union[Type, str] = None,
            use_class: Type = None,
            inject: list = None,
            imports: list = None
    ):
        d_module: DynamicModule = cls.for_root_app_async(value, factory, existing, use_class, inject, imports)
        return d_module
