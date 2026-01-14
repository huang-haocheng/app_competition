from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from acps_aip.aip_rpc_server import CommandHandlers, TaskManager, DefaultHandlers
from acps_aip.aip_base_model import (
    Message,
    Task,
    TaskState,
    TextDataItem,
    TaskCommand,
)
from base import extract_text_from_message


def _make_agent_message(task_id: str, session_id: str, agent_id: str, text: str) -> Message:
    return Message(
        id=f"msg-{uuid.uuid4()}",
        sentAt=datetime.now(timezone.utc).isoformat(),
        senderRole="partner",
        senderId=agent_id,
        command=TaskCommand.Get,
        dataItems=[TextDataItem(text=text)],
        taskId=task_id,
        sessionId=session_id,
    )


def make_single_turn_handlers(
    agent_id: str,
    processor: Callable[[str], str],
    *,
    empty_input_message: str = "请求内容为空，无法处理。",
    error_prefix: str = "处理请求时发生错误: ",
) -> CommandHandlers:
    """Create CommandHandlers for single-turn synchronous agents."""

    async def _process(message: Message, task: Task) -> Task:
        session_id = message.sessionId or task.sessionId or task.id
        if not task.sessionId:
            task.sessionId = session_id  # type: ignore[assignment]

        TaskManager.add_message_to_history(task.id, message)
        user_text = extract_text_from_message(message)
        if not user_text:
            failed = TaskManager.update_task_status(
                task.id,
                TaskState.Failed,
                data_items=[TextDataItem(text=empty_input_message)],
            )
            return failed

        try:
            result_text = await asyncio.to_thread(processor, user_text)
        except Exception as exc:  # pragma: no cover - defensive
            failed = TaskManager.update_task_status(
                task.id,
                TaskState.Failed,
                data_items=[TextDataItem(text=f"{error_prefix}{exc}")],
            )
            return failed

        agent_message = _make_agent_message(task.id, session_id, agent_id, result_text)
        TaskManager.add_message_to_history(task.id, agent_message)
        completed = TaskManager.update_task_status(
            task.id,
            TaskState.Completed,
            data_items=[TextDataItem(text=result_text)],
        )
        return completed

    async def on_start(message: Message, existing: Optional[Task]) -> Task:
        if existing:
            return await _process(message, existing)
        task = TaskManager.create_task(message, initial_state=TaskState.Accepted)
        return await _process(message, task)

    async def on_continue(message: Message, task: Task) -> Task:
        return await _process(message, task)

    return CommandHandlers(
        on_start=on_start,
        on_continue=on_continue,
        on_cancel=DefaultHandlers.cancel,
        on_complete=DefaultHandlers.complete,
    )
