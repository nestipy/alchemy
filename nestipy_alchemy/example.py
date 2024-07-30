import asyncio
import uuid
from typing import List

from sqlalchemy import String, ForeignKey, select, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship, DeclarativeBase, Session

from converter.parser import SqlAlchemyPydanticLoader
from converter.mapper import SqlAlchemyPydanticMapper

Base: DeclarativeBase = declarative_base()


class Employee(Base):
    __pydantic_name__ = "EmployeeSchema"
    __tablename__ = "employee"
    __pydantic_exclude__ = ["password_hash"]

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    department_id: Mapped[str] = mapped_column(String(36), ForeignKey("department.id"))
    department: Mapped["Department"] = relationship("Department", back_populates="employees")


class Department(Base):
    __pydantic_name__ = "DepartmentSchema"
    __tablename__ = "department"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    employees: Mapped[List[Employee]] = relationship("Employee", back_populates="department")


sqlalchemy_pydantic_mapper = SqlAlchemyPydanticMapper()


async def test_with_async():
    sqlalchemy_pydantic_mapper.type(model=Employee)(type("Employee", (), {}))
    engine = create_async_engine("mysql+asyncmy://root@localhost:3306/alchemy", echo=True)
    async with engine.begin() as conn:
        pass
    async with AsyncSession(bind=engine) as session:
        sqlalchemy_pydantic_loader = SqlAlchemyPydanticLoader(
            _mapper=sqlalchemy_pydantic_mapper,
            async_session_callback=lambda: session
        )
        stmt = select(Employee)
        result = await session.execute(stmt)
        all_employee = result.scalars().all()
        for employee in all_employee:
            json = await sqlalchemy_pydantic_loader.load(employee, depth=5)
            print(json.model_dump(mode="json"))
        await session.commit()


def test_with_sync():
    engine = create_engine("mysql+pymysql://root@localhost:3306/alchemy", echo=True)
    # Base.metadata.drop_all(bind=engine)
    # Base.metadata.create_all(bind=engine)
    sqlalchemy_pydantic_mapper.type(model=Employee)(type("Employee", (), {}))
    with Session(bind=engine, expire_on_commit=False) as session:
        # dep = Department(name="Test", employees=[Employee(name="Employee1", password_hash="test")])
        # session.add(dep)
        sqlalchemy_pydantic_loader = SqlAlchemyPydanticLoader(
            _mapper=sqlalchemy_pydantic_mapper,
            session=session
        )
        stmt = select(Employee)
        result = session.execute(stmt)
        all_employee = result.scalars().all()
        for employee in all_employee:
            json = sqlalchemy_pydantic_loader.load_sync(employee, depth=5)
            print(json.model_dump(mode="json"))
        session.commit()
    # print(sqlalchemy_pydantic_mapper.mapped_types.get("DepartmentSchema"))


if __name__ == "__main__":
    asyncio.run(test_with_async())
    # test_with_sync()
