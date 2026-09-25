import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Type
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import text, desc, func, inspect
from sqlalchemy.orm import load_only
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

    async def update(self, entity, updates=None, session=None):
        try:
            session = await self._write_session(session)
            # Similar to EF Core's nuclear Clear(), we ensure the instance is merged
            updated_entity = await session.merge(entity)

            if updates and len(updates) > 0:
                # Partial update logic
                for attr in updates:
                    val = getattr(entity, attr)
                    setattr(updated_entity, attr, val)
            else:
                # Full update logic - all attributes are updated
                inspected = inspect(entity)
                loaded_attrs = inspected.dict.keys() if inspected else dir(entity)
                for attr in loaded_attrs:
                    val = getattr(entity, attr)
                    setattr(updated_entity, attr, val)

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
