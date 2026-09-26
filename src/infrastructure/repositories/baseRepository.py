import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Type
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import text, desc, func, inspect
from sqlalchemy.orm import load_only, selectinload
from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from business.contextVars.sessionContext import session_context
from business.contextVars.requestContext import request_context
from core.iRepositories.iBaseRepository import IBaseRepository
from core.dtos.baseDtos import BaseResponseDto
from core.utils.entitiesHandler import EntitiesHandler
from core.utils.timezoneHandler import TimezoneHandler


class BaseRepository(IBaseRepository):
    def __init__(
        self,
        session: AsyncSession | None,
        model: Type,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        self._session = session
        self._model = model
        self._session_factory = session_factory

    def _resolve_session(self) -> AsyncSession | None:
        request_session = session_context.get(None)
        if request_session is not None:
            return request_session
        if self._session is not None:
            return self._session
        if self._session_factory is None:
            raise RuntimeError("No active database session found for this request")
        return None

    @asynccontextmanager
    async def _read_session(self, session: AsyncSession | None = None):
        """Use an active request transaction, or a temporary session for one read."""
        if session is not None:
            yield session
            return

        request_session = session_context.get(None)
        if request_session is not None:
            yield request_session
            return

        if self._session is not None:
            yield self._session
            return

        if self._session_factory is None:
            raise RuntimeError("No database session or session factory available")

        read_session = self._session_factory()
        session_token = session_context.set(read_session)
        try:
            yield read_session
        except Exception:
            # A failed read must end its transaction before the connection is released.
            try:
                if read_session.in_transaction():
                    await read_session.rollback()
            except Exception:
                pass
            raise
        finally:
            # Do not rollback a successful read here. SQLAlchemy expires ORM state on
            # rollback, so the returned objects would become expired/detached before
            # the caller can use their already-loaded attributes. Closing the session
            # is sufficient to release the connection; the DB transaction is ended as
            # part of closing the session/connection.
            session_context.reset(session_token)
            try:
                await read_session.close()
            except Exception:
                pass

    async def _write_session(self, session: AsyncSession | None = None) -> AsyncSession:
        """Lazily create the request session and begin a transaction for a mutation."""
        request_session = session_context.get(None)
        session = session or request_session or self._session

        context_session_created = False
        context_token = None

        if session is None:
            if self._session_factory is None:
                raise RuntimeError("No database session or session factory available")
            session = self._session_factory()
            context_token = session_context.set(session)
            context_session_created = True
        elif request_session is None:
            session_context.set(session)

        try:
            if not session.in_transaction():
                await session.begin()
            return session
        except Exception:
            if context_session_created and context_token is not None:
                session_context.reset(context_token)
                try:
                    await session.close()
                except Exception:
                    pass
            raise

    async def _execute_isolated_sql(self, command: str, params: dict | None = None):
        if not self._session_factory:
            session = self._resolve_session()
            if session is None:
                raise RuntimeError("No database session or session factory available")
            return await session.execute(text(command), params or {})

        async with self._session_factory() as isolated_session:
            result = await isolated_session.execute(text(command), params or {})
            await isolated_session.commit()
            return result

    async def _log_error(
        self,
        action: str,
        level: str,
        code: int,
        message: str,
        details: dict | None = None,
        source: str = "",
        route: str = "",
        ip: str = "",
        user_id: int | None = None,
        created_at: datetime = TimezoneHandler.now("UTC"),
        updated_at: datetime = TimezoneHandler.now("UTC"),
    ):
        max_message_len = 2000
        safe_message = message if isinstance(message, str) else str(message)
        if len(safe_message) > max_message_len:
            safe_message = safe_message[: max_message_len - 3] + "..."

        formatted_details = (
            json.dumps(details, default=str) if details is not None else None
        )

        query = f"INSERT INTO {EntitiesHandler.TABLES.get('Log')} (action, entity, level, response_code, message, details, source, route, ip, user_id, created_at, updated_at) VALUES (:action, :entity, :level, :response_code, :message, :details, :source, :route, :ip, :user_id, :created_at, :updated_at)"
        params = {
            "action": action,
            "entity": self._model.__name__,
            "level": level,
            "response_code": code,
            "message": safe_message,
            "details": formatted_details,
            "source": source,
            "route": route,
            "ip": ip,
            "user_id": user_id,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        return await self._execute_isolated_sql(query, params)

    async def find_one(
        self,
        predicate=None,
        includes=None,
        selects=None,
        order_by=None,
        session=None,
    ):
        try:
            async with self._read_session(session) as session:
                query = select(self._model)

                # Handling Predicates
                if predicate is not None:
                    query = query.where(predicate)

                # Handling Dynamic Includes (Multilevel nested includes)
                if includes:
                    for include in includes:
                        query = query.options(include)

                # Handling Projections (Selects)
                if selects and len(selects) > 0:
                    query = query.options(load_only(*selects))

                # Ordering
                if order_by:
                    for ob in order_by:
                        query = query.order_by(ob)

                result = await session.execute(query)
                entity = result.scalars().first()

                return BaseResponseDto(
                    success=True,
                    data=entity,
                    message="Found Successfully",
                    code=200,
                )
        except Exception as ex:
            await self._log_error(
                action="FindOne",
                level="error",
                code=500,
                message=f"An error occurred while searching for {self._model.__name__}",
                details={"error": repr(ex)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=None,
                message="An error occurred while searching for the entity",
                code=500,
                error=repr(ex),
            )

    async def find(
        self,
        predicate=None,
        includes=None,
        selects=None,
        order_by=None,
        page=1,
        limit=50,
        session=None,
    ):
        try:
            async with self._read_session(session) as session:
                query = select(self._model)

                # Handling Predicates
                if predicate is not None:
                    query = query.where(predicate)

                # Handling Dynamic Includes (Multilevel nested includes)
                if includes:
                    for include in includes:
                        query = query.options(include)

                # Handling Projections (Selects)
                if selects and len(selects) > 0:
                    query = query.options(load_only(*selects))

                # Ordering
                if order_by:
                    for ob in order_by:
                        query = query.order_by(ob)

                # Pagination
                query = query.offset((page - 1) * limit).limit(limit + 1)

                result = await session.execute(query)
                entities = result.scalars().all()

                return BaseResponseDto(
                    success=True,
                    data=(
                        list(entities[:-1]) if len(entities) > limit else list(entities)
                    ),
                    message="Found Successfully",
                    code=200,
                    next_page=len(entities) > limit,
                )
        except Exception as ex:
            await self._log_error(
                action="Find",
                level="error",
                code=500,
                message=f"An error occurred while searching for {self._model.__name__}s",
                details={"error": repr(ex)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=[],
                message="Search Failed",
                code=500,
                error=repr(ex),
            )

    async def count(self, predicate=None, session=None):
        try:
            async with self._read_session(session) as session:
                query = select(func.count(getattr(self._model, "id")))

                if predicate is not None:
                    query = query.where(predicate)

                result = await session.execute(query)
                count = result.scalar()

                return BaseResponseDto(
                    success=True,
                    data=count if count else 0,
                    message="Count Retrieved Successfully",
                    code=200,
                )
        except Exception as ex:
            await self._log_error(
                action="Count",
                level="error",
                code=500,
                message=f"An error occurred while counting {self._model.__name__}s",
                details={"error": repr(ex)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=0,
                message="Count Failed",
                code=500,
                error=repr(ex),
            )

    async def find_distinct(
        self,
        predicate=None,
        column=None,
        session=None,
    ):
        try:
            async with self._read_session(session) as session:
                if column is None:
                    return BaseResponseDto(
                        success=False,
                        data=[],
                        message="Column must be provided for distinct query",
                        code=400,
                    )

                query = select(column).distinct()

                if predicate is not None:
                    query = query.where(predicate)

                result = await session.execute(query)
                distinct_values = result.scalars().all()

                return BaseResponseDto(
                    success=True,
                    data=list(distinct_values),
                    message="Distinct Values Retrieved Successfully",
                    code=200,
                )
        except Exception as ex:
            await self._log_error(
                action="FindDistinct",
                level="error",
                code=500,
                message=f"An error occurred while retrieving distinct values for {self._model.__name__}",
                details={"error": repr(ex)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=[],
                message="Distinct Query Failed",
                code=500,
                error=repr(ex),
            )

    async def create(self, entity, session=None):
        try:
            session = await self._write_session(session)
            session.add(entity)
            await session.flush()
            await session.refresh(entity)
            return BaseResponseDto(
                success=True,
                data=entity,
                message="Entity Added Successfully",
                code=201,
            )
        except IntegrityError as ie:
            await self._log_error(
                action="Create",
                level="error",
                code=400,
                message=f"Integrity error while creating {self._model.__name__}",
                details={"error": repr(ie)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=None,
                message=f"User Tried to create a duplicated {self._model.__name__} Violating Unique Constraints",
                error=repr(ie),
                code=400,
            )
        except Exception as ex:
            await self._log_error(
                action="Create",
                level="error",
                code=500,
                message=f"An error occurred while creating {self._model.__name__}",
                details={"error": repr(ex)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=None,
                message=f"Error Creating {self._model.__name__}",
                error=repr(ex),
                code=500,
            )

    def _complete_primary_key(self, mapper, instance):
        values = mapper.primary_key_from_instance(instance)
        return values if values and all(value is not None for value in values) else None

    def _unique_column_sets(self, mapper):
        unique_sets = []
        for constraint in mapper.local_table.constraints:
            if getattr(constraint, "unique", False):
                columns = tuple(column.key for column in constraint.columns)
                if columns:
                    unique_sets.append(columns)
        for index in mapper.local_table.indexes:
            if index.unique:
                columns = tuple(
                    column.key for column in index.columns if hasattr(column, "key")
                )
                if columns:
                    unique_sets.append(columns)
        return unique_sets

    def _source_column_values(self, source, mapper, relationship_property, parent):
        values = {}
        source_state = inspect(source)
        source_data = source_state.dict

        for column in mapper.columns:
            if column.key in source_data:
                values[column.key] = source_data[column.key]

        for local_column, remote_column in relationship_property.local_remote_pairs:
            parent_value = getattr(parent, local_column.key, None)
            if parent_value is not None:
                values[remote_column.key] = parent_value

        for relationship in mapper.relationships:
            if relationship.uselist:
                continue
            related = source_data.get(relationship.key)
            if related is None:
                continue
            related_pk = self._complete_primary_key(relationship.mapper, related)
            if related_pk is None:
                continue
            for local_column, remote_column in relationship.local_remote_pairs:
                remote_index = list(relationship.mapper.primary_key).index(
                    remote_column
                )
                values[local_column.key] = related_pk[remote_index]

        return values

    def _identities_for_values(self, mapper, values):
        identities = []
        primary_key = tuple(values.get(column.key) for column in mapper.primary_key)
        if primary_key and all(value is not None for value in primary_key):
            identities.append(("pk", primary_key))

        for columns in self._unique_column_sets(mapper):
            key = tuple(values.get(column) for column in columns)
            if key and all(value is not None for value in key):
                identities.append(("unique", columns, key))

        return identities

    def _identity_for_values(self, mapper, values):
        identities = self._identities_for_values(mapper, values)
        return identities[0] if identities else None

    async def _hydrate_child_relationships(
        self, session, child, child_mapper, column_values, parent_mapper
    ):
        for relationship in child_mapper.relationships:
            if relationship.uselist or relationship.mapper is parent_mapper:
                continue

            related_primary_key = []
            valid = True
            for local_column, remote_column in relationship.local_remote_pairs:
                value = column_values.get(local_column.key)
                if value is None:
                    valid = False
                    break
                related_primary_key.append((remote_column, value))

            if not valid or not related_primary_key:
                continue

            remote_pk_columns = list(relationship.mapper.primary_key)
            remote_values = [None] * len(remote_pk_columns)
            for remote_column, value in related_primary_key:
                try:
                    remote_index = remote_pk_columns.index(remote_column)
                except ValueError:
                    valid = False
                    break
                remote_values[remote_index] = value

            if not valid or any(value is None for value in remote_values):
                continue

            related = await session.get(
                relationship.mapper.class_, tuple(remote_values)
            )
            if related is not None:
                setattr(child, relationship.key, related)

    async def _reconcile_collection_relationship(
        self, session, parent, source, relationship_property
    ):
        child_mapper = relationship_property.mapper
        child_class = child_mapper.class_
        current_collection = getattr(parent, relationship_property.key)
        current_children = list(current_collection)

        current_by_identity = {}
        for child in current_children:
            child_values = {
                column.key: getattr(child, column.key, None)
                for column in child_mapper.columns
            }
            for identity in self._identities_for_values(child_mapper, child_values):
                current_by_identity[identity] = child

        desired_children = []
        seen_identities = set()
        source_children = (
            source
            if isinstance(source, (list, tuple, set))
            else getattr(source, relationship_property.key, None)
        )

        for source_child in list(source_children or []):
            source_values = self._source_column_values(
                source_child, child_mapper, relationship_property, parent
            )
            identity = self._identity_for_values(child_mapper, source_values)

            managed_child = current_by_identity.get(identity) if identity else None

            if managed_child is None and identity and identity[0] == "pk":
                managed_child = await session.get(child_class, identity[1])

            if managed_child is None and identity and identity[0] == "unique":
                conditions = [
                    getattr(child_class, column) == value
                    for column, value in zip(identity[1], identity[2])
                ]
                result = await session.execute(select(child_class).where(*conditions))
                managed_child = result.scalars().first()

            if managed_child is None:
                child_kwargs = {}
                for column in child_mapper.columns:
                    value = source_values.get(column.key)
                    if column.primary_key and value is None:
                        continue
                    if value is not None:
                        child_kwargs[column.key] = value
                managed_child = child_class(**child_kwargs)

            managed_identity = self._identity_for_values(
                child_mapper,
                {
                    column.key: getattr(managed_child, column.key, None)
                    for column in child_mapper.columns
                },
            )
            if managed_identity is not None:
                if managed_identity in seen_identities:
                    continue
                seen_identities.add(managed_identity)

            desired_children.append(managed_child)

        desired_set = (
            set(desired_children) if isinstance(current_collection, set) else None
        )

        for current_child in current_children:
            should_keep = (
                current_child in desired_set
                if desired_set is not None
                else current_child in desired_children
            )
            if not should_keep:
                current_collection.remove(current_child)

        existing = (
            set(current_collection)
            if desired_set is not None
            else list(current_collection)
        )
        for desired_child in desired_children:
            if desired_child not in existing:
                if desired_set is not None:
                    current_collection.add(desired_child)
                else:
                    current_collection.append(desired_child)

        for desired_child in desired_children:
            await self._hydrate_child_relationships(
                session,
                desired_child,
                child_mapper,
                {
                    column.key: getattr(desired_child, column.key, None)
                    for column in child_mapper.columns
                },
                relationship_property.parent,
            )

        return parent

    async def _reconcile_relationship_updates(
        self,
        session,
        managed_entity,
        source_entity,
        mapper,
        attributes,
        relationship_sources=None,
    ):
        relationship_sources = relationship_sources or {}
        with session.no_autoflush:
            for attr in attributes:
                relationship_property = mapper.relationships.get(attr)
                if relationship_property is None:
                    continue

                source_value = relationship_sources.get(attr)
                if relationship_property.uselist:
                    await self._reconcile_collection_relationship(
                        session,
                        managed_entity,
                        source_value if source_value is not None else source_entity,
                        relationship_property,
                    )
                else:
                    source_value = (
                        source_value
                        if source_value is not None
                        else inspect(source_entity).dict.get(attr)
                    )
                    if source_value is not None or attr in inspect(source_entity).dict:
                        await self._reconcile_scalar_relationship_value(
                            session,
                            managed_entity,
                            source_value,
                            relationship_property,
                        )

    async def _reconcile_scalar_relationship_value(
        self, session, parent, related, relationship_property
    ):
        if related is None:
            setattr(parent, relationship_property.key, None)
            return parent

        related_mapper = relationship_property.mapper
        identity = self._complete_primary_key(related_mapper, related)
        if identity is not None:
            managed_related = await session.get(related_mapper.class_, identity)
            if managed_related is None:
                raise ValueError(
                    f"{related_mapper.class_.__name__} with primary key {identity} was not found"
                )
            setattr(parent, relationship_property.key, managed_related)
            return parent

        if inspect(related).transient:
            setattr(parent, relationship_property.key, related)
            return parent

        raise ValueError(
            f"Cannot update relationship '{relationship_property.key}' with an entity that has no primary key"
        )

    async def update(self, entity, updates=None, session=None):
        try:
            session = await self._write_session(session)

            inspected_entity = inspect(entity)
            mapper = inspected_entity.mapper
            pk_values = self._complete_primary_key(mapper, entity)

            if pk_values is None:
                await self._log_error(
                    action="Update",
                    level="error",
                    code=400,
                    message=f"Cannot update {self._model.__name__} without a complete primary key",
                    details={"primary_key": mapper.primary_key_from_instance(entity)},
                    source="BaseRepository",
                )
                return BaseResponseDto(
                    success=False,
                    data=None,
                    message=f"Cannot update {self._model.__name__} without a complete primary key",
                    code=400,
                )

            if updates and len(updates) > 0:
                attrs_to_update = []
                for attr in updates:
                    if attr in attrs_to_update or attr in inspected_entity.unloaded:
                        continue
                    descriptor = mapper.all_orm_descriptors.get(attr)
                    if not hasattr(entity, attr) and not isinstance(
                        descriptor, AssociationProxy
                    ):
                        continue
                    attrs_to_update.append(attr)
            else:
                mapped_attributes = [attr.key for attr in mapper.column_attrs] + [
                    relationship.key for relationship in mapper.relationships
                ]
                attrs_to_update = [
                    attr
                    for attr in mapped_attributes
                    if attr not in inspected_entity.unloaded
                ]

            requested_attributes = set(attrs_to_update)
            normalized_attributes = []
            relationship_sources = {}
            for attr in attrs_to_update:
                descriptor = mapper.all_orm_descriptors.get(attr)
                if isinstance(descriptor, AssociationProxy):
                    target_relationship = descriptor.target_collection
                    if target_relationship in requested_attributes:
                        continue
                    relationship_property = mapper.relationships.get(
                        target_relationship
                    )
                    if (
                        relationship_property is None
                        or target_relationship in relationship_sources
                    ):
                        continue
                    proxy_values = getattr(entity, attr)
                    if relationship_property.uselist:
                        relationship_sources[target_relationship] = [
                            descriptor.creator(value) for value in (proxy_values or [])
                        ]
                    else:
                        relationship_sources[target_relationship] = (
                            descriptor.creator(proxy_values)
                            if proxy_values is not None
                            else None
                        )
                    normalized_attributes.append(target_relationship)
                    continue
                normalized_attributes.append(attr)
            attrs_to_update = list(dict.fromkeys(normalized_attributes))

            relationship_names = set(mapper.relationships.keys())
            relationship_attributes = [
                attr for attr in attrs_to_update if attr in relationship_names
            ]
            scalar_attributes = [
                attr for attr in attrs_to_update if attr not in relationship_names
            ]

            get_options = [
                selectinload(getattr(self._model, attr))
                for attr in relationship_attributes
            ]
            updated_entity = await session.get(
                self._model,
                pk_values,
                options=get_options or None,
            )

            if not updated_entity:
                await self._log_error(
                    action="Update",
                    level="error",
                    code=404,
                    message=f"{self._model.__name__} not found for update",
                    details={"entity": repr(entity)},
                    source="BaseRepository",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"{self._model.__name__} not found for update",
                )

            for attr in scalar_attributes:
                if hasattr(entity, attr) and attr not in inspected_entity.unloaded:
                    setattr(updated_entity, attr, getattr(entity, attr))

            if relationship_attributes:
                await self._reconcile_relationship_updates(
                    session,
                    updated_entity,
                    entity,
                    mapper,
                    relationship_attributes,
                    relationship_sources,
                )

            await session.flush()
            return BaseResponseDto(
                success=True,
                data=updated_entity,
                message="Updated Successfully",
                code=200,
            )
        except StaleDataError as sde:
            await self._log_error(
                action="Update",
                level="error",
                code=409,
                message=f"Stale data error while updating {self._model.__name__}",
                details={"error": repr(sde)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=None,
                message=f"Another concurrent operation has modified the {self._model.__name__} you are trying to update. Please try again later.",
                error=repr(sde),
                code=409,
            )
        except IntegrityError as ie:
            await self._log_error(
                action="Update",
                level="error",
                code=400,
                message=f"Integrity error while updating {self._model.__name__}",
                details={"error": repr(ie)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=None,
                message=f"User Tried to update a duplicated {self._model.__name__} Violating Unique Constraints",
                error=repr(ie),
                code=400,
            )
        except Exception as ex:
            await self._log_error(
                action="Update",
                level="error",
                code=500,
                message=f"An error occurred while updating {self._model.__name__}",
                details={"error": repr(ex)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=None,
                message="Update Failed",
                code=500,
                error=repr(ex),
            )

    async def delete(self, entity, session=None):
        try:
            session = await self._write_session(session)
            merged = await session.merge(entity)
            await session.delete(merged)
            await session.flush()
            return BaseResponseDto(
                success=True, data=True, message="Deleted Successfully", code=200
            )
        except StaleDataError as sde:
            await self._log_error(
                action="Delete",
                level="error",
                code=409,
                message=f"Stale data error while deleting {self._model.__name__}",
                details={"error": repr(sde)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=False,
                message=f"Another concurrent operation has modified the {self._model.__name__} you are trying to delete. Please try again later.",
                error=repr(sde),
                code=409,
            )
        except Exception as ex:
            await self._log_error(
                action="Delete",
                level="error",
                code=500,
                message=f"An error occurred while deleting {self._model.__name__}",
                details={"error": repr(ex)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=False,
                message="Delete Failed",
                code=500,
                error=repr(ex),
            )

    async def execute_sql(self, command, params=None, session=None):
        try:
            if session is None:
                session = self._resolve_session()
            if self._session_factory is None:
                if session is None:
                    raise RuntimeError(
                        "No database session or session factory available"
                    )
                await session.execute(text(command), params or {})
                await session.commit()
            else:
                await self._execute_isolated_sql(command, params)
            return BaseResponseDto(
                success=True, data=True, message="SQL Executed", code=200
            )
        except Exception as ex:
            await self._log_error(
                action="ExecuteSQL",
                level="error",
                code=500,
                message=f"An error occurred while executing SQL",
                details={"error": repr(ex)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=False,
                message="SQL Execution Failed",
                code=500,
                error=repr(ex),
            )

    async def execute_stored_function(self, function_name, params=None, session=None):
        try:
            async with self._read_session(session) as session:
                if not params:
                    params = {}
                param_placeholders = ", ".join([f":{key}" for key in params.keys()])
                command = f"SELECT {function_name}({param_placeholders})"
                result = await session.execute(text(command), params)
                await session.flush()
                return BaseResponseDto(
                    success=True,
                    data=result.scalar(),
                    message="Stored Function Executed",
                    code=200,
                )
        except Exception as ex:
            await self._log_error(
                action="ExecuteStoredFunction",
                level="error",
                code=500,
                message=f"An error occurred while executing stored function {function_name}",
                details={"error": repr(ex)},
                source="BaseRepository",
            )
            return BaseResponseDto(
                success=False,
                data=None,
                message="Stored Function Execution Failed",
                code=500,
                error=repr(ex),
            )

    async def begin_transaction(self, session=None):
        try:
            await self._write_session(session)
        except Exception as ex:
            await self._log_error(
                action="BeginTransaction",
                level="error",
                code=500,
                message=f"An error occurred while beginning the transaction.",
                details={"error": repr(ex)},
                source="BaseRepository",
            )

    async def commit_transaction(self, session=None):
        try:
            if session is None:
                session = session_context.get(None)
            if session is None or not session.in_transaction():
                return
            request = request_context.get(None)
            if request and await request.is_disconnected():
                await session.rollback()
                return
            await session.commit()
        except Exception as ex:
            await self._log_error(
                action="CommitTransaction",
                level="error",
                code=500,
                message=f"An error occurred while committing the transaction.",
                details={"error": repr(ex)},
                source="BaseRepository",
            )

    async def rollback_transaction(self, session=None):
        try:
            if session is None:
                session = session_context.get(None)
            if session is None or not session.in_transaction():
                return
            await session.rollback()
        except Exception as ex:
            await self._log_error(
                action="RollbackTransaction",
                level="error",
                code=500,
                message=f"An error occurred while rolling back the transaction.",
                details={"error": repr(ex)},
                source="BaseRepository",
            )
