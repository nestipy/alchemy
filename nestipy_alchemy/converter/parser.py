from collections import defaultdict
from datetime import datetime
from types import NoneType
from typing import List, Callable, Any, Dict, cast, Mapping, Tuple

from pydantic import BaseModel
from sqlalchemy import select, inspect, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapper, InstanceState, MANYTOONE
from sqlalchemy.orm import RelationshipProperty, Session

from mapper import SqlAlchemyPydanticMapper


class SqlAlchemyPydanticLoader:
    _default_python = (
        int, str, float, dict, bool, complex,
        bytes, datetime, bytearray, tuple, frozenset, type,
        NoneType
    )

    def __init__(
            self,
            _mapper: "SqlAlchemyPydanticMapper",
            session: Session = None,
            async_session_context: Callable[[], AsyncSession] = None
    ):
        self._mapper = _mapper
        self.session = session
        self.async_session_context = async_session_context

    def load_sync(self, db_instance: Any, depth: int = 5) -> BaseModel:
        model = type(db_instance)
        schema_name = getattr(model, "__pydantic_name__", model.__name__)
        pydantic_model = self._mapper.mapped_types.get(schema_name)
        if not pydantic_model:
            pydantic_model = self._mapper.type(model)(type(schema_name, (), {}))
        data = self._serialize_sync(db_instance, pydantic_model, depth)
        return pydantic_model.model_validate(data, context="test")

    def _serialize_sync(self, db_instance: Any, pydantic_model: BaseModel, depth: int = 3) -> Dict[str, Any]:
        if depth <= 0:
            return {}
        data = {}
        fields = pydantic_model.model_fields.keys()
        mapper: Mapper = cast(Mapper, inspect(type(db_instance)))
        for column_name, column_key in mapper.columns.items():
            if column_name in fields:
                value = getattr(db_instance, column_name)
                data[column_name] = value

        for field_name, field_type in mapper.all_orm_descriptors.items():
            if field_name not in fields or not isinstance(field_type.property, RelationshipProperty):
                continue
            value = getattr(db_instance, field_name)
            if isinstance(value, list):
                if depth - 1 == 0:
                    data[field_name] = []
                else:
                    data[field_name] = [
                        self._serialize_sync(item, self._mapper.mapped_types.get(
                            getattr(item, "__pydantic_name__", type(item).__name__)
                        ), depth - 1) for item in
                        value
                    ]
            else:
                if depth - 1 == 0:
                    data[field_name] = None
                else:
                    data[field_name] = self._serialize_sync(value, self._mapper.mapped_types.get(
                        getattr(value, "__pydantic_name__", type(value).__name__)
                    ), depth - 1)

        return data

    async def load(self, db_instance: Any, depth: int = 5) -> BaseModel:
        model = type(db_instance)
        schema_name = getattr(model, "__pydantic_name__", model.__name__)
        pydantic_model = self._mapper.mapped_types.get(schema_name)
        if not pydantic_model:
            pydantic_model = self._mapper.type(model)(type(schema_name, (), {}))
        data = await self._serialize(db_instance, pydantic_model, depth)
        return pydantic_model.model_validate(data, context="test")

    async def _serialize(self, db_instance: Any, pydantic_model: BaseModel, depth: int = 3) -> Dict[str, Any]:
        if depth <= 0:
            return {}
        data = {}
        fields = pydantic_model.model_fields.keys()
        mapper: Mapper = cast(Mapper, inspect(type(db_instance)))
        for column_name, column_key in mapper.columns.items():
            if column_name in fields:
                value = getattr(db_instance, column_name)
                data[column_name] = value

        for field_name, field_type in mapper.all_orm_descriptors.items():
            if field_name not in fields or not isinstance(field_type.property, RelationshipProperty):
                continue
            value = await self.relationship_resolver_for(db_instance, field_type.property)
            if isinstance(value, list):
                if depth - 1 == 0:
                    data[field_name] = []
                else:
                    data[field_name] = [
                        await self._serialize(item, self._mapper.mapped_types.get(
                            getattr(item, "__pydantic_name__", type(item).__name__)
                        ), depth - 1) for item in
                        value[0]
                    ]
            elif not isinstance(value, self._default_python):
                if depth - 1 == 0:
                    data[field_name] = None
                else:
                    data[field_name] = await self._serialize(value, self._mapper.mapped_types.get(
                        getattr(value, "__pydantic_name__", type(value).__name__)
                    ), depth - 1)
            else:
                data[field_name] = value
        return data

    async def relationship_resolver_for(
            self,
            instance: Any,
            _relationship: RelationshipProperty,
    ) -> Any:
        instance_state = cast(InstanceState, inspect(instance))
        if _relationship.key not in instance_state.unloaded:
            related_objects = getattr(instance, _relationship.key)
        else:
            _relationship_key = tuple(
                [
                    getattr(instance, local.key)
                    for local, _ in _relationship.local_remote_pairs or []
                    if local.key
                ]
            )
            if any(item is None for item in _relationship_key):
                if _relationship.uselist:
                    return []
                else:
                    return None

            related_objects = await self.loader_for(_relationship, [_relationship_key])
        return related_objects[0] if _relationship.direction == MANYTOONE else related_objects

    async def loader_for(
            self,
            _relationship: RelationshipProperty,
            keys: List[Tuple]
    ) -> Any:
        related_model = _relationship.entity.entity
        filters = tuple_(
            *[remote for _, remote in _relationship.local_remote_pairs or []]
        ).in_(keys)
        query = select(related_model).filter(filters)
        if _relationship.order_by:
            query = query.order_by(*_relationship.order_by)
        rows = await self._scalars_all(query)

        def group_by_remote_key(row: Any) -> Tuple:
            return tuple(
                [
                    getattr(row, remote.key)
                    for _, remote in _relationship.local_remote_pairs or []
                    if remote.key
                ]
            )

        grouped_keys: Mapping[Tuple, List[Any]] = defaultdict(list)
        for row in rows:
            grouped_keys[group_by_remote_key(row)].append(row)
        if _relationship.uselist:
            return [grouped_keys[key] for key in keys]
        else:
            return [
                grouped_keys[key][0] if grouped_keys[key] else None
                for key in keys
            ]

    async def _scalars_all(self, *args, **kwargs):
        if self.async_session_context:
            async with self.async_session_context() as bind:
                return (await bind.scalars(*args, **kwargs)).all()
        else:
            assert self.session is not None, "No session binding"
            return self.session.scalars(*args, **kwargs).all()