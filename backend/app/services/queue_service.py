"""Queue service for dispatching function and agent jobs via arq."""
import asyncio
import json
import logging
import uuid
from typing import Any, Optional

from app.core.config import settings
from app.core.redis import get_arq_pool, get_redis

logger = logging.getLogger(__name__)

# Redis key prefixes
JOB_STATUS_PREFIX = "sinas:job:status:"
JOB_RESULT_PREFIX = "sinas:job:result:"
JOB_DONE_CHANNEL_PREFIX = "sinas:job:done:"
DLQ_KEY = "sinas:queue:dlq"
JOB_TTL = 86400  # 24 hours


class QueueService:
    """Service for enqueuing and tracking jobs."""

    async def enqueue_function(
        self,
        function_namespace: str,
        function_name: str,
        input_data: dict[str, Any],
        execution_id: str,
        trigger_type: str,
        trigger_id: str,
        user_id: str,
        chat_id: Optional[str] = None,
        delay: Optional[int] = None,
    ) -> str:
        """
        Enqueue a function execution job.

        Returns:
            job_id (str)
        """
        pool = await get_arq_pool()
        redis = await get_redis()

        job_id = str(uuid.uuid4())

        # Set initial status in Redis
        await redis.set(
            f"{JOB_STATUS_PREFIX}{job_id}",
            json.dumps({"status": "queued", "execution_id": execution_id}),
            ex=JOB_TTL,
        )

        # Build kwargs for arq job
        job_kwargs = {
            "job_id": job_id,
            "function_namespace": function_namespace,
            "function_name": function_name,
            "input_data": input_data,
            "execution_id": execution_id,
            "trigger_type": trigger_type,
            "trigger_id": trigger_id,
            "user_id": user_id,
            "chat_id": chat_id,
        }

        # Enqueue with optional delay
        enqueue_kwargs = {"_job_id": job_id, "_queue_name": "sinas:queue:functions"}
        if delay:
            enqueue_kwargs["_defer_by"] = delay

        await pool.enqueue_job(
            "execute_function_job",
            **job_kwargs,
            **enqueue_kwargs,
        )

        logger.info(
            f"Enqueued function job {job_id}: {function_namespace}/{function_name} "
            f"(execution_id={execution_id})"
        )
        return job_id

    async def get_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        """Get job status from Redis."""
        redis = await get_redis()
        data = await redis.get(f"{JOB_STATUS_PREFIX}{job_id}")
        if data:
            return json.loads(data)
        return None

    async def get_job_result(self, job_id: str) -> Optional[Any]:
        """Get job result from Redis."""
        redis = await get_redis()
        data = await redis.get(f"{JOB_RESULT_PREFIX}{job_id}")
        if data:
            return json.loads(data)
        return None

    async def enqueue_and_wait(
        self,
        function_namespace: str,
        function_name: str,
        input_data: dict[str, Any],
        execution_id: str,
        trigger_type: str,
        trigger_id: str,
        user_id: str,
        chat_id: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Any:
        """
        Enqueue a function job and wait for its result.

        Uses Redis pub/sub to get notified when the job completes.
        """
        redis = await get_redis()
        timeout = timeout or settings.queue_default_timeout

        job_id = await self.enqueue_function(
            function_namespace=function_namespace,
            function_name=function_name,
            input_data=input_data,
            execution_id=execution_id,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            user_id=user_id,
            chat_id=chat_id,
        )

        # Subscribe to completion channel
        channel = f"{JOB_DONE_CHANNEL_PREFIX}{execution_id}"
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)

        try:
            # Poll for result with timeout
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg["type"] == "message":
                    result_data = json.loads(msg["data"])
                    if result_data.get("status") == "failed":
                        raise Exception(result_data.get("error", "Job failed"))
                    return result_data.get("result")

                # Also check if result is already stored (race condition safety)
                status = await self.get_job_status(job_id)
                if status and status.get("status") == "completed":
                    result = await self.get_job_result(job_id)
                    return result
                elif status and status.get("status") == "failed":
                    raise Exception(status.get("error", "Job failed"))

            raise TimeoutError(
                f"Job {job_id} timed out after {timeout}s"
            )
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def enqueue_agent_message(
        self,
        chat_id: str,
        user_id: str,
        user_token: str,
        content: str,
        channel_id: str,
    ) -> str:
        """Enqueue an agent message processing job."""
        pool = await get_arq_pool()
        redis = await get_redis()

        job_id = str(uuid.uuid4())

        await redis.set(
            f"{JOB_STATUS_PREFIX}{job_id}",
            json.dumps({"status": "queued", "channel_id": channel_id}),
            ex=JOB_TTL,
        )

        await pool.enqueue_job(
            "execute_agent_message_job",
            job_id=job_id,
            chat_id=chat_id,
            user_id=user_id,
            user_token=user_token,
            content=content,
            channel_id=channel_id,
            _job_id=job_id,
            _queue_name="sinas:queue:agents",
        )

        logger.info(f"Enqueued agent message job {job_id} for chat {chat_id}")
        return job_id

    async def enqueue_agent_resume(
        self,
        chat_id: str,
        user_id: str,
        user_token: str,
        pending_approval_id: str,
        approved: bool,
        channel_id: str,
    ) -> str:
        """Enqueue an agent resume job (after tool approval)."""
        pool = await get_arq_pool()
        redis = await get_redis()

        job_id = str(uuid.uuid4())

        await redis.set(
            f"{JOB_STATUS_PREFIX}{job_id}",
            json.dumps({"status": "queued", "channel_id": channel_id}),
            ex=JOB_TTL,
        )

        await pool.enqueue_job(
            "execute_agent_resume_job",
            job_id=job_id,
            chat_id=chat_id,
            user_id=user_id,
            user_token=user_token,
            pending_approval_id=pending_approval_id,
            approved=approved,
            channel_id=channel_id,
            _job_id=job_id,
            _queue_name="sinas:queue:agents",
        )

        logger.info(f"Enqueued agent resume job {job_id} for chat {chat_id}")
        return job_id


# Global instance
queue_service = QueueService()
