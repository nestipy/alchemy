from dataclasses import asdict
from typing import Annotated

from nestipy.common import Injectable
from nestipy.ioc import Inject
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from dto import CreateUserDto
from nestipy_alchemy import SQLAlchemyService
from user_model import User, UserWithRelation, UserModel, Video


@Injectable()
class AppService:
    db_service: Annotated[SQLAlchemyService, Inject()]

    async def get(self):
        async with self.db_service.session as session:
            stmt = select(User).options(selectinload(User.videos)).order_by(User.created_at)
            query = await session.execute(stmt)
            users = query.scalars().all()
            users_models = [UserWithRelation.model_validate(user).model_dump(mode='json') for user in users]
            await session.close()
        return users_models

    async def post(self, data: CreateUserDto):
        async with self.db_service.session as session:
            user = User(
                **asdict(data)
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            result = await session.execute(
                select(User).where(User.id == user.id).order_by(User.id).options(
                    selectinload(User.comments),
                    selectinload(User.videos).selectinload(Video.comments)))
            new_user = result.scalar()
            user_model = UserWithRelation.model_validate(new_user, strict=False).model_dump(mode='json')
            await session.close()
        return user_model

    @classmethod
    async def put(cls, id_: int, data: dict):
        return "test"

    @classmethod
    async def delete(cls, id_: int):
        return "test"
