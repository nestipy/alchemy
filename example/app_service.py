from dataclasses import asdict
from typing import Annotated

from nestipy.common import Injectable
from nestipy.ioc import Inject
from sqlalchemy.future import select

from nestipy_alchemy import SQLAlchemyService
from user_model import User, UserModel
from dto import CreateUserDto


@Injectable()
class AppService:
    db_service: Annotated[SQLAlchemyService, Inject()]

    async def get(self):
        async with self.db_service.session as session:
            stmt = select(User).order_by(User.create_date)
            query = await session.execute(stmt)
            await session.close()
        return [UserModel.model_validate(user[0]).model_dump(mode='json') for user in query.fetchall()]

    async def post(self, data: CreateUserDto):
        async with self.db_service.session as session:
            user = User(
                **asdict(data)
            )
            session.add(user)
            await session.flush()
            await session.commit()
            user_model = UserModel.model_validate(user).model_dump(mode='json')
        return user_model

    @classmethod
    async def put(cls, id_: int, data: dict):
        return "test"

    @classmethod
    async def delete(cls, id_: int):
        return "test"
