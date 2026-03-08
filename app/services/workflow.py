"""
Workflow I/O service — manages task input/output definitions and instances.
Forms a DAG of data flow between tasks.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import TaskIODefinition, TaskIOInstance


async def create_io_definition(
    db: AsyncSession,
    *,
    task_definition_id: uuid.UUID,
    io_type: str,
    data_key: str,
    data_type: str,
    description: str | None = None,
    required: bool = True,
    source_task_definition_id: uuid.UUID | None = None,
) -> TaskIODefinition:
    io_def = TaskIODefinition(
        task_definition_id=task_definition_id,
        io_type=io_type,
        data_key=data_key,
        data_type=data_type,
        description=description,
        required=required,
        source_task_definition_id=source_task_definition_id,
    )
    db.add(io_def)
    await db.flush()
    await db.refresh(io_def)
    return io_def


async def list_io_definitions(
    db: AsyncSession,
    task_definition_id: uuid.UUID | None = None,
    io_type: str | None = None,
) -> list[TaskIODefinition]:
    query = select(TaskIODefinition)
    if task_definition_id:
        query = query.where(TaskIODefinition.task_definition_id == task_definition_id)
    if io_type:
        query = query.where(TaskIODefinition.io_type == io_type)
    query = query.order_by(TaskIODefinition.data_key)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_io_instance(
    db: AsyncSession,
    *,
    task_io_definition_id: uuid.UUID,
    task_instance_id: uuid.UUID,
    project_id: uuid.UUID,
    data: dict | None = None,
) -> TaskIOInstance:
    status = "AVAILABLE" if data is not None else "NOT_AVAILABLE"
    io_inst = TaskIOInstance(
        task_io_definition_id=task_io_definition_id,
        task_instance_id=task_instance_id,
        project_id=project_id,
        data=data,
        status=status,
        produced_at=datetime.now(timezone.utc) if data else None,
    )
    db.add(io_inst)
    await db.flush()
    await db.refresh(io_inst)
    return io_inst


async def update_io_instance(
    db: AsyncSession,
    io_instance_id: uuid.UUID,
    **updates,
) -> TaskIOInstance:
    result = await db.execute(
        select(TaskIOInstance).where(TaskIOInstance.id == io_instance_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise ValueError("Task IO instance not found")

    for field, value in updates.items():
        if value is not None and hasattr(inst, field):
            setattr(inst, field, value)

    # Auto-set produced_at when data is provided
    if "data" in updates and updates["data"] is not None:
        inst.status = "AVAILABLE"
        inst.produced_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(inst)
    return inst


async def list_io_instances(
    db: AsyncSession,
    *,
    task_instance_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[TaskIOInstance]:
    query = select(TaskIOInstance)
    if task_instance_id:
        query = query.where(TaskIOInstance.task_instance_id == task_instance_id)
    if project_id:
        query = query.where(TaskIOInstance.project_id == project_id)
    if status:
        query = query.where(TaskIOInstance.status == status)
    query = query.order_by(TaskIOInstance.task_instance_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_task_inputs(
    db: AsyncSession,
    task_instance_id: uuid.UUID,
) -> list[TaskIOInstance]:
    """Get all input IO instances for a task."""
    result = await db.execute(
        select(TaskIOInstance)
        .join(TaskIODefinition, TaskIOInstance.task_io_definition_id == TaskIODefinition.id)
        .where(
            TaskIOInstance.task_instance_id == task_instance_id,
            TaskIODefinition.io_type == "INPUT",
        )
    )
    return list(result.scalars().all())


async def get_task_outputs(
    db: AsyncSession,
    task_instance_id: uuid.UUID,
) -> list[TaskIOInstance]:
    """Get all output IO instances for a task."""
    result = await db.execute(
        select(TaskIOInstance)
        .join(TaskIODefinition, TaskIOInstance.task_io_definition_id == TaskIODefinition.id)
        .where(
            TaskIOInstance.task_instance_id == task_instance_id,
            TaskIODefinition.io_type == "OUTPUT",
        )
    )
    return list(result.scalars().all())
