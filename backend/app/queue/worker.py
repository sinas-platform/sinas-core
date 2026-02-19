"""arq worker definitions for function and agent execution."""
import json
import logging
from typing import Any

from app.core.config import settings
from app.core.redis import get_redis_settings
from app.services.queue_service import (
    DLQ_KEY,
    JOB_RESULT_PREFIX,
    JOB_STATUS_PREFIX,
    JOB_TTL,
    JOB_DONE_CHANNEL_PREFIX,
)

logger = logging.getLogger(__name__)


async def execute_function_job(ctx: dict, **kwargs: Any) -> Any:
    """
    Execute a function in the worker process.

    Called by arq when a function job is dequeued.
    Delegates to the existing executor.execute_function().
    """
    from redis.asyncio import Redis

    job_id = kwargs["job_id"]
    function_namespace = kwargs["function_namespace"]
    function_name = kwargs["function_name"]
    input_data = kwargs["input_data"]
    execution_id = kwargs["execution_id"]
    trigger_type = kwargs["trigger_type"]
    trigger_id = kwargs["trigger_id"]
    user_id = kwargs["user_id"]
    chat_id = kwargs.get("chat_id")

    redis: Redis = ctx.get("redis") or Redis.from_url(settings.redis_url, decode_responses=True)

    logger.info(
        f"Worker executing function {function_namespace}/{function_name} "
        f"(job={job_id}, execution={execution_id})"
    )

    # Update status to running
    await redis.set(
        f"{JOB_STATUS_PREFIX}{job_id}",
        json.dumps({"status": "running", "execution_id": execution_id}),
        ex=JOB_TTL,
    )

    try:
        from app.services.execution_engine import executor

        result = await executor.execute_function(
            function_namespace=function_namespace,
            function_name=function_name,
            input_data=input_data,
            execution_id=execution_id,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            user_id=user_id,
            chat_id=chat_id,
        )

        # Store result
        await redis.set(
            f"{JOB_RESULT_PREFIX}{job_id}",
            json.dumps(result, default=str),
            ex=JOB_TTL,
        )

        # Update status to completed
        await redis.set(
            f"{JOB_STATUS_PREFIX}{job_id}",
            json.dumps({"status": "completed", "execution_id": execution_id}),
            ex=JOB_TTL,
        )

        # Notify waiters via pub/sub
        await redis.publish(
            f"{JOB_DONE_CHANNEL_PREFIX}{execution_id}",
            json.dumps({"status": "completed", "result": result}, default=str),
        )

        logger.info(f"Function job {job_id} completed successfully")
        return result

    except Exception as e:
        logger.error(f"Function job {job_id} failed: {e}")

        # Update status to failed
        await redis.set(
            f"{JOB_STATUS_PREFIX}{job_id}",
            json.dumps({
                "status": "failed",
                "execution_id": execution_id,
                "error": str(e),
            }),
            ex=JOB_TTL,
        )

        # Notify waiters of failure
        await redis.publish(
            f"{JOB_DONE_CHANNEL_PREFIX}{execution_id}",
            json.dumps({"status": "failed", "error": str(e)}),
        )

        # Check if retries exhausted (arq handles retry count internally)
        job_try = ctx.get("job_try", 1)
        if job_try >= settings.queue_max_retries:
            # Push to dead letter queue
            await redis.lpush(
                DLQ_KEY,
                json.dumps({
                    "job_id": job_id,
                    "function": f"{function_namespace}/{function_name}",
                    "execution_id": execution_id,
                    "error": str(e),
                    "attempts": job_try,
                }),
            )
            logger.warning(f"Job {job_id} moved to DLQ after {job_try} attempts")

        raise  # Re-raise for arq retry


async def function_worker_startup(ctx: dict) -> None:
    """arq startup hook for function workers.

    Initializes Redis, discovers existing shared worker containers (created
    by the backend), and starts the per-user container cleanup task.
    """
    from redis.asyncio import Redis

    ctx["redis"] = Redis.from_url(settings.redis_url, decode_responses=True)

    # Discover shared worker containers (created by backend, not by us)
    from app.services.shared_worker_manager import shared_worker_manager

    await shared_worker_manager._discover_existing_workers()
    shared_worker_manager._initialized = True
    print(f"✅ Discovered {len(shared_worker_manager.workers)} shared workers")

    # Discover existing pool containers (created by backend leader)
    from app.services.container_pool import container_pool

    await container_pool._discover_existing_containers()
    container_pool._initialized = True
    print(f"✅ Discovered {len(container_pool.idle)} pool containers")

    logger.info("Function worker started")


async def agent_worker_startup(ctx: dict) -> None:
    """arq startup hook for agent workers.

    Initializes Redis and eagerly imports app modules to avoid cold-start
    latency on the first job.
    """
    from redis.asyncio import Redis

    ctx["redis"] = Redis.from_url(settings.redis_url, decode_responses=True)

    # Eagerly import heavy modules so first job doesn't pay import cost
    from app.services.message_service import MessageService  # noqa: F401
    from app.core.database import AsyncSessionLocal  # noqa: F401

    logger.info("Agent worker started")


async def shutdown(ctx: dict) -> None:
    """arq worker shutdown hook."""
    redis = ctx.get("redis")
    if redis:
        await redis.aclose()
    logger.info("Worker stopped")


class WorkerSettings:
    """arq worker settings for function execution."""

    functions = [execute_function_job]
    on_startup = function_worker_startup
    on_shutdown = shutdown
    redis_settings = get_redis_settings()
    queue_name = "sinas:queue:functions"
    max_jobs = settings.queue_function_concurrency
    job_timeout = settings.queue_default_timeout
    max_tries = settings.queue_max_retries
    retry_delay = settings.queue_retry_delay


# Import agent jobs for combined worker
from app.queue.agent_jobs import (
    execute_agent_message_job,
    execute_agent_resume_job,
)


class AgentWorkerSettings:
    """arq worker settings for agent message processing."""

    functions = [execute_agent_message_job, execute_agent_resume_job]
    on_startup = agent_worker_startup
    on_shutdown = shutdown
    redis_settings = get_redis_settings()
    queue_name = "sinas:queue:agents"
    max_jobs = settings.queue_agent_concurrency
    job_timeout = 600  # 10 minutes for long conversations
    max_tries = 1  # No retry for agent conversations (side effects)
