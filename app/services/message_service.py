"""Message service for chat processing with tool calling."""
import json
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chat, Message, Assistant, Memory, RequestLog
from app.providers import create_provider
from app.services.webhook_tools import WebhookToolConverter
from app.services.mcp import mcp_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class MessageService:
    """Service for processing chat messages with LLM and tool calling."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.webhook_converter = WebhookToolConverter()

    async def send_message(
        self,
        chat_id: str,
        user_id: str,
        user_token: str,
        content: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        inject_memories: bool = False,
        enabled_webhooks: Optional[List[str]] = None,
        disabled_webhooks: Optional[List[str]] = None,
        enabled_mcp_tools: Optional[List[str]] = None,
        disabled_mcp_tools: Optional[List[str]] = None,
    ) -> Message:
        """
        Send a message and get LLM response (non-streaming).

        Args:
            chat_id: Chat ID
            user_id: User ID
            user_token: User's JWT or API key
            content: Message content
            provider: LLM provider name
            model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            inject_memories: Whether to inject memories into context
            enabled_webhooks: Override enabled webhooks
            disabled_webhooks: Disabled webhooks
            enabled_mcp_tools: Override enabled MCP tools
            disabled_mcp_tools: Disabled MCP tools

        Returns:
            Assistant's response message
        """
        # Get chat
        result = await self.db.execute(
            select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise ValueError("Chat not found")

        # Save user message
        user_message = Message(
            chat_id=chat_id,
            role="user",
            content=content,
            enabled_webhooks=enabled_webhooks,
            enabled_mcp_tools=enabled_mcp_tools
        )
        self.db.add(user_message)
        await self.db.commit()
        await self.db.refresh(user_message)

        # Build conversation history
        messages = await self._build_conversation_history(
            chat, inject_memories, user_id
        )

        # Get available tools
        tools = await self._get_available_tools(
            user_id=user_id,
            chat=chat,
            message_enabled_webhooks=enabled_webhooks,
            message_disabled_webhooks=disabled_webhooks,
            message_enabled_mcp=enabled_mcp_tools,
            message_disabled_mcp=disabled_mcp_tools
        )

        # Create LLM provider
        llm_provider = create_provider(provider, model)

        # Get response from LLM
        start_time = datetime.now(timezone.utc)
        response = await llm_provider.complete(
            messages=messages,
            model=model or settings.default_model,
            tools=tools if tools else None,
            temperature=temperature,
            max_tokens=max_tokens
        )
        end_time = datetime.now(timezone.utc)

        # Log request
        await self._log_request(
            user_id=user_id,
            chat_id=str(chat_id),
            message_id=str(user_message.id),
            provider=provider or "openai",
            model=model or settings.default_model,
            messages=messages,
            response=response,
            latency_ms=int((end_time - start_time).total_seconds() * 1000)
        )

        # Handle tool calls if present
        if response.get("tool_calls"):
            return await self._handle_tool_calls(
                chat_id=chat_id,
                user_id=user_id,
                user_token=user_token,
                messages=messages,
                tool_calls=response["tool_calls"],
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools
            )

        # Save assistant message
        assistant_message = Message(
            chat_id=chat_id,
            role="assistant",
            content=response.get("content", ""),
            enabled_webhooks=enabled_webhooks,
            enabled_mcp_tools=enabled_mcp_tools
        )
        self.db.add(assistant_message)
        await self.db.commit()
        await self.db.refresh(assistant_message)

        return assistant_message

    async def stream_message(
        self,
        chat_id: str,
        user_id: str,
        user_token: str,
        content: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        inject_memories: bool = False,
        enabled_webhooks: Optional[List[str]] = None,
        disabled_webhooks: Optional[List[str]] = None,
        enabled_mcp_tools: Optional[List[str]] = None,
        disabled_mcp_tools: Optional[List[str]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send a message and stream LLM response.

        Yields:
            Dict chunks with response data
        """
        # Get chat
        result = await self.db.execute(
            select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise ValueError("Chat not found")

        # Save user message
        user_message = Message(
            chat_id=chat_id,
            role="user",
            content=content,
            enabled_webhooks=enabled_webhooks,
            enabled_mcp_tools=enabled_mcp_tools
        )
        self.db.add(user_message)
        await self.db.commit()
        await self.db.refresh(user_message)

        # Build conversation history
        messages = await self._build_conversation_history(
            chat, inject_memories, user_id
        )

        # Get available tools
        tools = await self._get_available_tools(
            user_id=user_id,
            chat=chat,
            message_enabled_webhooks=enabled_webhooks,
            message_disabled_webhooks=disabled_webhooks,
            message_enabled_mcp=enabled_mcp_tools,
            message_disabled_mcp=disabled_mcp_tools
        )

        # Create LLM provider
        llm_provider = create_provider(provider, model)

        # Stream response
        full_content = ""
        tool_calls = []

        async for chunk in llm_provider.stream(
            messages=messages,
            model=model or settings.default_model,
            tools=tools if tools else None,
            temperature=temperature,
            max_tokens=max_tokens
        ):
            if chunk.get("content"):
                full_content += chunk["content"]

            if chunk.get("tool_calls"):
                tool_calls.extend(chunk["tool_calls"])

            yield chunk

        # Save assistant message after streaming completes
        assistant_message = Message(
            chat_id=chat_id,
            role="assistant",
            content=full_content if full_content else None,
            tool_calls=tool_calls if tool_calls else None,
            enabled_webhooks=enabled_webhooks,
            enabled_mcp_tools=enabled_mcp_tools
        )
        self.db.add(assistant_message)
        await self.db.commit()

        # Handle tool calls if present
        if tool_calls:
            # Execute tools and get final response (but don't yield it since streaming is done)
            await self._handle_tool_calls(
                chat_id=chat_id,
                user_id=user_id,
                user_token=user_token,
                messages=messages,
                tool_calls=tool_calls,
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools
            )

    async def _build_conversation_history(
        self,
        chat: Chat,
        inject_memories: bool,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Build conversation history for LLM."""
        messages = []

        # Add system prompt from assistant if exists
        if chat.assistant_id:
            result = await self.db.execute(
                select(Assistant).where(Assistant.id == chat.assistant_id)
            )
            assistant = result.scalar_one_or_none()
            if assistant and assistant.system_prompt:
                messages.append({
                    "role": "system",
                    "content": assistant.system_prompt
                })

        # Inject memories if requested
        if inject_memories:
            result = await self.db.execute(
                select(Memory).where(Memory.user_id == user_id)
            )
            memories = result.scalars().all()
            if memories:
                memory_content = "# Memories\n\n"
                for memory in memories:
                    memory_content += f"**{memory.key}**: {memory.value}\n"
                messages.append({
                    "role": "system",
                    "content": memory_content
                })

        # Add chat message history
        result = await self.db.execute(
            select(Message).where(Message.chat_id == chat.id).order_by(Message.created_at)
        )
        chat_messages = result.scalars().all()

        for msg in chat_messages:
            message_dict = {"role": msg.role}

            # Always include content, even if None (required for assistant messages with tool_calls)
            message_dict["content"] = msg.content

            if msg.tool_calls:
                message_dict["tool_calls"] = msg.tool_calls

            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id

            if msg.name:
                message_dict["name"] = msg.name

            messages.append(message_dict)

        return messages

    async def _get_available_tools(
        self,
        user_id: str,
        chat: Chat,
        message_enabled_webhooks: Optional[List[str]],
        message_disabled_webhooks: Optional[List[str]],
        message_enabled_mcp: Optional[List[str]],
        message_disabled_mcp: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Get all available tools (webhooks + MCP)."""
        tools = []

        # Determine webhook configuration
        webhook_enabled = message_enabled_webhooks or chat.enabled_webhooks or None
        webhook_disabled = message_disabled_webhooks or []

        # Get webhook tools
        webhook_tools = await self.webhook_converter.get_available_webhooks(
            db=self.db,
            user_id=user_id,
            enabled_webhooks=webhook_enabled,
            disabled_webhooks=webhook_disabled
        )
        tools.extend(webhook_tools)

        # Determine MCP configuration
        mcp_enabled = message_enabled_mcp or chat.enabled_mcp_tools or None

        # Get MCP tools
        mcp_tools = await mcp_client.get_available_tools(
            enabled_tools=mcp_enabled
        )
        tools.extend(mcp_tools)

        return tools

    async def _handle_tool_calls(
        self,
        chat_id: str,
        user_id: str,
        user_token: str,
        messages: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]],
        provider: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        tools: List[Dict[str, Any]]
    ) -> Message:
        """Execute tool calls and get final response."""
        # Save assistant message with tool calls
        assistant_message = Message(
            chat_id=chat_id,
            role="assistant",
            content=None,
            tool_calls=tool_calls
        )
        self.db.add(assistant_message)
        await self.db.commit()

        # Execute each tool call
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            arguments_str = tool_call["function"]["arguments"]
            arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str

            # Execute tool (webhook or MCP)
            try:
                if tool_name in mcp_client.tools:
                    result = await mcp_client.execute_tool(tool_name, arguments)
                else:
                    result = await self.webhook_converter.execute_webhook_tool(
                        db=self.db,
                        tool_name=tool_name,
                        arguments=arguments,
                        user_token=user_token
                    )

                result_content = json.dumps(result) if not isinstance(result, str) else result

            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                result_content = json.dumps({"error": str(e)})

            # Save tool result message
            tool_message = Message(
                chat_id=chat_id,
                role="tool",
                content=result_content,
                tool_call_id=tool_call["id"],
                name=tool_name
            )
            self.db.add(tool_message)

        await self.db.commit()

        # Get final response from LLM with tool results
        # Rebuild messages with tool results
        result = await self.db.execute(
            select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
        )
        updated_messages = []
        for msg in result.scalars().all():
            message_dict = {"role": msg.role}
            if msg.content:
                message_dict["content"] = msg.content
            if msg.tool_calls:
                message_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id
            if msg.name:
                message_dict["name"] = msg.name
            updated_messages.append(message_dict)

        llm_provider = create_provider(provider, model)
        final_response = await llm_provider.complete(
            messages=updated_messages,
            model=model or settings.default_model,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Save final assistant message
        final_message = Message(
            chat_id=chat_id,
            role="assistant",
            content=final_response.get("content", "")
        )
        self.db.add(final_message)
        await self.db.commit()
        await self.db.refresh(final_message)

        return final_message

    async def _log_request(
        self,
        user_id: str,
        chat_id: str,
        message_id: str,
        provider: str,
        model: str,
        messages: List[Dict[str, Any]],
        response: Dict[str, Any],
        latency_ms: int
    ):
        """Log LLM request for analytics."""
        usage = response.get("usage", {})

        log = RequestLog(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            provider=provider,
            model=model,
            request_data={"messages": messages},
            response_data=response,
            tokens_prompt=usage.get("prompt_tokens"),
            tokens_completion=usage.get("completion_tokens"),
            tokens_total=usage.get("total_tokens"),
            latency_ms=latency_ms,
            status_code=200
        )
        self.db.add(log)
        await self.db.commit()
