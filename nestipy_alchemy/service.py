from typing import Annotated

from nestipy.common import Injectable
from nestipy.core import OnInit, OnDestroy
from nestipy.ioc import Inject
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine

from .builder import SQLAlchemyOption, SQLALCHEMY_OPTION


@Injectable()
class SQLAlchemyService(OnInit, OnDestroy):
    _option: Annotated[SQLAlchemyOption, Inject(SQLALCHEMY_OPTION)]
    _engine: AsyncEngine = None
    _session: AsyncSession = None

    async def on_startup(self):
        if not self._engine:
            self._engine = create_async_engine(self._option.url, echo=self._option.echo)

        if self._option.sync:
            async with self._engine.begin() as conn:
                await conn.run_sync(self._option.declarative_base.metadata.drop_all)
                await conn.run_sync(self._option.declarative_base.metadata.create_all)

    async def on_shutdown(self):
        await self._engine.dispose()

    @property
    def session(self) -> AsyncSession:
        if not self._session:
            self._session = AsyncSession(self._engine)
        return self._session

    @property
    def engine(self) -> AsyncEngine:
        return self._engine
