import uuid
from datetime import datetime
from types import NoneType
from typing import Container, Optional, Type, List, Callable, Union, Any, Dict

from pydantic import BaseModel, ConfigDict, create_model
from sqlalchemy import String, ForeignKey, create_engine, select
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import RelationshipProperty, relationship, Session
from sqlalchemy.orm import declarative_base, DeclarativeBase
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm.relationships import MANYTOONE, ONETOMANY, MANYTOMANY

orm_config = ConfigDict(from_attributes=True)


class SqlAlchemyPydanticLoader:
    _default_python = (
        int, str, float, dict, bool, complex,
        bytes, datetime, bytearray, tuple, frozenset, type,
        NoneType
    )

    def __init__(self, _mapper: "SqlAlchemyPydanticMapper"):
        self._mapper = _mapper

    def load(self, db_instance: Any, depth: int = 5) -> BaseModel:
        model = type(db_instance)
        schema_name = getattr(model, "__pydantic_name__", model.__name__)
        pydantic_model = self._mapper.get(schema_name)
        if not pydantic_model:
            pydantic_model = self._mapper.type(model)(type(schema_name, (), {}))
        data = self._serialize(db_instance, pydantic_model, depth)
        return pydantic_model.model_validate(data, context="test")

    def _serialize(self, db_instance: Any, pydantic_model: BaseModel, depth: int = 3) -> Dict[str, Any]:
        if depth <= 0:
            return {}
        data = {}
        annotations = pydantic_model.model_fields
        for field_name, field_type in annotations.items():
            value = getattr(db_instance, field_name)
            if isinstance(value, list):
                if depth - 1 == 0:
                    data[field_name] = []
                else:
                    data[field_name] = [
                        self._serialize(item, self._mapper.get(
                            getattr(item, "__pydantic_name__", type(item).__name__)
                        ), depth - 1) for item in
                        value
                    ]
            elif not isinstance(value, self._default_python):
                if depth - 1 == 0:
                    data[field_name] = None
                else:
                    data[field_name] = self._serialize(value, self._mapper.get(
                        getattr(value, "__pydantic_name__", type(value).__name__)
                    ), depth - 1)
            else:
                data[field_name] = value
        return data


class SqlAlchemyPydanticMapper:
    _models_registry = {}

    def type(
            self,
            model: Type, *,
            config: Type = None,
            exclude: Container[str] = None,
            model_name: str = None
    ) -> Callable[[Type], Type[BaseModel]]:
        def _mapper(cls: Type) -> Type[BaseModel]:
            return self._to_pydantic(
                db_model=model,
                config=config or getattr(model, "__pydantic__config__", getattr(cls, "__pydantic__config__", None)),
                exclude=[*(exclude or []), *getattr(cls, "__pydantic_exclude__", [])],
                model_name=model_name
            )

        return _mapper

    def _to_pydantic(
            self,
            db_model: Type, *,
            config: Type = None,
            exclude: Container[str] = None,
            model_name: str = None
    ) -> Type[BaseModel]:
        table = db_model.metadata.tables[db_model.__tablename__]
        new_model_name = getattr(db_model, "__pydantic_name__", model_name or db_model.__name__)
        if new_model_name in self._models_registry:
            return self._models_registry[new_model_name]

        fields = {}
        exclude = [*(exclude or []), *getattr(db_model, "__pydantic_exclude__", [])]
        for column in table.columns:
            name = column.name
            if name in exclude:
                continue
            python_type: Optional[type] = None
            if hasattr(column.type, "impl"):
                if hasattr(column.type.impl, "python_type"):
                    python_type = column.type.impl.python_type
            elif hasattr(column.type, "python_type"):
                python_type = column.type.python_type
            assert python_type, f"Could not infer python_type for {column}"

            if not column.nullable:
                fields[name] = (python_type, ...)
            else:
                fields[name] = (Optional[python_type], None)

        pydantic_model = create_model(new_model_name, __config__=config or orm_config, **fields)
        self._models_registry[new_model_name] = pydantic_model

        for attr_name, attr_value in db_model.__dict__.items():
            if attr_name in exclude:
                continue
            if (
                    attr_value is not None
                    and not isinstance(attr_value, str)
                    and hasattr(attr_value, "property")
                    and isinstance(attr_value.property, RelationshipProperty)
            ):
                related_model = getattr(attr_value.property.mapper, "class_")
                related_model_schema = self._to_pydantic(related_model)
                relationship_type = attr_value.property.direction

                if relationship_type == ONETOMANY:
                    fields[attr_name] = (List[related_model_schema], [])
                elif relationship_type == MANYTOONE:
                    fields[attr_name] = (Optional[related_model_schema], None)
                elif relationship_type == MANYTOMANY:
                    fields[attr_name] = (List[related_model_schema], None)
                else:
                    fields[attr_name] = (Optional[related_model_schema], None)

        model = create_model(new_model_name, **fields, __base__=pydantic_model)
        model.model_rebuild(raise_errors=False)
        self._models_registry[new_model_name] = model
        return model

    def get(self, key: str) -> Union[BaseModel, None]:
        return self._models_registry.get(key)


Base: DeclarativeBase = declarative_base()


class Employee(Base):
    __pydantic_name__ = "EmployeeSchema"
    __tablename__ = "employee"
    __pydantic_exclude__ = ["password_hash", "department", "department_id"]

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
sqlalchemy_pydantic_loader = SqlAlchemyPydanticLoader(_mapper=sqlalchemy_pydantic_mapper)

if __name__ == "__main__":
    engine = create_engine("mysql+pymysql://root@localhost:3306/alchemy", echo=True)
    # Base.metadata.drop_all(bind=engine)
    # Base.metadata.create_all(bind=engine)
    sqlalchemy_pydantic_mapper.type(model=Employee)(type("Employee", (), {}))
    with Session(bind=engine, expire_on_commit=False) as session:
        # dep = Department(name="Test", employees=[Employee(name="Employee1", password_hash="test")])
        # session.add(dep)
        stmt = select(Employee)
        result = session.execute(stmt)
        all_employee = result.scalars().all()
        for employee in all_employee:
            json = sqlalchemy_pydantic_loader.load(employee, depth=2)
            print(json.model_dump(mode="json"))
        session.commit()

    print(sqlalchemy_pydantic_mapper.get("DepartmentSchema"))
