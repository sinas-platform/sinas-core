"""Dynamic OpenAPI specification generator for runtime API."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any

from app.models.webhook import Webhook
from app.models.agent import Agent
from app.models.function import Function


async def generate_runtime_openapi(db: AsyncSession) -> Dict[str, Any]:
    """
    Generate dynamic OpenAPI specification for runtime API.

    Shows all active webhooks and agents with their schemas.
    """
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "SINAS Runtime API",
            "version": "1.0.0",
            "description": "Execute AI agents, webhooks, and continue conversations"
        },
        "servers": [
            {
                "url": "/",
                "description": "Runtime API Server"
            }
        ],
        "paths": {},
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                },
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            }
        }
    }

    # Add webhook endpoints
    webhook_result = await db.execute(
        select(Webhook).where(Webhook.is_active == True)
    )
    webhooks = webhook_result.scalars().all()

    for webhook in webhooks:
        # Load associated function to get schemas
        function = await Function.get_by_name(db, webhook.function_namespace, webhook.function_name)

        path = f"/webhooks/{webhook.path}"
        method = webhook.http_method.lower()

        if path not in spec["paths"]:
            spec["paths"][path] = {}

        spec["paths"][path][method] = {
            "summary": webhook.description or f"Execute {webhook.function_namespace}/{webhook.function_name}",
            "tags": ["runtime-webhooks"],
            "operationId": f"execute_webhook_{webhook.path.replace('/', '_')}_{method}",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": function.input_schema if function and function.input_schema else {"type": "object"}
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Function executed successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "success": {"type": "boolean"},
                                    "execution_id": {"type": "string", "format": "uuid"},
                                    "result": function.output_schema if function and function.output_schema else {"type": "object"}
                                }
                            }
                        }
                    }
                },
                "401": {
                    "description": "Authentication required"
                },
                "404": {
                    "description": "Webhook not found"
                },
                "500": {
                    "description": "Function execution failed"
                }
            }
        }

        # Add security if required
        if webhook.requires_auth:
            spec["paths"][path][method]["security"] = [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]

    # Add agent chat creation endpoints
    agent_result = await db.execute(
        select(Agent).where(Agent.is_active == True)
    )
    agents = agent_result.scalars().all()

    for agent in agents:
        path = f"/agents/{agent.namespace}/{agent.name}/chats"

        # Build request schema for chat creation with optional input
        input_schema_props = agent.input_schema if agent.input_schema else {"type": "object"}
        request_schema = {
            "type": "object",
            "properties": {
                "input": {
                    **input_schema_props,
                    "description": "Structured input for system prompt templating (validated against agent's input_schema)"
                },
                "title": {"type": "string", "description": "Optional title for the chat (defaults to 'Chat with {namespace}/{name}')"}
            }
        }

        spec["paths"][path] = {
            "post": {
                "summary": f"Create chat with {agent.namespace}/{agent.name}",
                "description": f"Create new chat with the {agent.namespace}/{agent.name} agent. Returns chat object. Use POST /chats/{{chat_id}}/messages to send messages.",
                "tags": ["runtime-agents"],
                "operationId": f"create_chat_with_{agent.namespace}_{agent.name}".replace('-', '_').replace('.', '_'),
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": request_schema
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Chat created successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string", "format": "uuid"},
                                        "user_id": {"type": "string", "format": "uuid"},
                                        "group_id": {"type": "string", "format": "uuid"},
                                        "agent_id": {"type": "string", "format": "uuid"},
                                        "agent_namespace": {"type": "string"},
                                        "agent_name": {"type": "string"},
                                        "title": {"type": "string"},
                                        "created_at": {"type": "string", "format": "date-time"},
                                        "updated_at": {"type": "string", "format": "date-time"}
                                    }
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Input validation failed"
                    },
                    "404": {
                        "description": "Agent not found"
                    }
                },
                "security": []  # Optional auth
            }
        }

    # Add chat message sending endpoint
    spec["paths"]["/chats/{chat_id}/messages"] = {
        "post": {
            "summary": "Send message to chat",
            "description": "Send a message to an existing chat and get LLM response. All agent behavior (LLM, tools, context) is defined by the agent.",
            "tags": ["runtime-chats"],
            "operationId": "send_message",
            "parameters": [
                {
                    "name": "chat_id",
                    "in": "path",
                    "required": True,
                    "schema": {
                        "type": "string",
                        "format": "uuid"
                    },
                    "description": "Chat ID from chat creation"
                }
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["content"],
                            "properties": {
                                "content": {
                                    "oneOf": [
                                        {"type": "string"},
                                        {"type": "array", "items": {"type": "object"}}
                                    ],
                                    "description": "Message content (string for text, array for multimodal: images, audio, files)"
                                }
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Message sent successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "format": "uuid"},
                                    "chat_id": {"type": "string", "format": "uuid"},
                                    "role": {"type": "string"},
                                    "content": {"type": "string"},
                                    "tool_calls": {"type": "array"},
                                    "created_at": {"type": "string", "format": "date-time"}
                                }
                            }
                        }
                    }
                },
                "403": {
                    "description": "Not authorized"
                },
                "404": {
                    "description": "Chat not found"
                }
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        }
    }

    # Add chat management endpoints
    spec["paths"]["/chats"] = {
        "get": {
            "summary": "List chats",
            "description": "List all chats for current user",
            "tags": ["runtime-chats"],
            "operationId": "list_chats",
            "responses": {
                "200": {
                    "description": "List of chats",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string", "format": "uuid"},
                                        "title": {"type": "string"},
                                        "agent_id": {"type": "string", "format": "uuid"},
                                        "agent_namespace": {"type": "string"},
                                        "agent_name": {"type": "string"},
                                        "created_at": {"type": "string", "format": "date-time"},
                                        "updated_at": {"type": "string", "format": "date-time"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        }
    }

    spec["paths"]["/chats/{chat_id}"] = {
        "get": {
            "summary": "Get chat with messages",
            "description": "Get specific chat and all its messages",
            "tags": ["runtime-chats"],
            "operationId": "get_chat",
            "parameters": [
                {"name": "chat_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}}
            ],
            "responses": {
                "200": {
                    "description": "Chat with messages",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "format": "uuid"},
                                    "title": {"type": "string"},
                                    "messages": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "string", "format": "uuid"},
                                                "role": {"type": "string"},
                                                "content": {"type": "string"},
                                                "created_at": {"type": "string", "format": "date-time"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "404": {"description": "Chat not found"}
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        },
        "put": {
            "summary": "Update chat",
            "description": "Update chat title",
            "tags": ["runtime-chats"],
            "operationId": "update_chat",
            "parameters": [
                {"name": "chat_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}}
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"}
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {"description": "Chat updated successfully"},
                "404": {"description": "Chat not found"}
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        },
        "delete": {
            "summary": "Delete chat",
            "description": "Delete chat and all its messages",
            "tags": ["runtime-chats"],
            "operationId": "delete_chat",
            "parameters": [
                {"name": "chat_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}}
            ],
            "responses": {
                "204": {"description": "Chat deleted successfully"},
                "404": {"description": "Chat not found"}
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        }
    }

    # Add chat message streaming endpoint
    spec["paths"]["/chats/{chat_id}/messages/stream"] = {
        "post": {
            "summary": "Stream message to chat",
            "description": "Send a message and stream LLM response via SSE",
            "tags": ["runtime-chats"],
            "operationId": "stream_message",
            "parameters": [
                {
                    "name": "chat_id",
                    "in": "path",
                    "required": True,
                    "schema": {
                        "type": "string",
                        "format": "uuid"
                    },
                    "description": "Chat ID from chat creation"
                }
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["content"],
                            "properties": {
                                "content": {
                                    "oneOf": [
                                        {"type": "string"},
                                        {"type": "array", "items": {"type": "object"}}
                                    ],
                                    "description": "Message content (string for text, array for multimodal: images, audio, files)"
                                }
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "SSE stream of message chunks",
                    "content": {
                        "text/event-stream": {
                            "schema": {
                                "type": "string",
                                "description": "Server-Sent Events stream"
                            }
                        }
                    }
                },
                "403": {
                    "description": "Not authorized"
                },
                "404": {
                    "description": "Chat not found"
                }
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        }
    }

    # Add authentication endpoints
    spec["paths"]["/auth/login"] = {
        "post": {
            "summary": "Request OTP login",
            "description": "Send OTP code to email for passwordless authentication",
            "tags": ["runtime-auth"],
            "operationId": "request_otp",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["email"],
                            "properties": {
                                "email": {"type": "string", "format": "email"}
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "OTP sent successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "message": {"type": "string"},
                                    "session_id": {"type": "string", "format": "uuid"}
                                }
                            }
                        }
                    }
                }
            },
            "security": []
        }
    }

    spec["paths"]["/auth/verify-otp"] = {
        "post": {
            "summary": "Verify OTP and get tokens",
            "description": "Exchange OTP code for access and refresh tokens",
            "tags": ["runtime-auth"],
            "operationId": "verify_otp",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["session_id", "otp_code"],
                            "properties": {
                                "session_id": {"type": "string", "format": "uuid"},
                                "otp_code": {"type": "string", "minLength": 6, "maxLength": 6}
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Authentication successful",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "access_token": {"type": "string"},
                                    "refresh_token": {"type": "string"},
                                    "token_type": {"type": "string"},
                                    "expires_in": {"type": "integer"},
                                    "user": {"type": "object"}
                                }
                            }
                        }
                    }
                },
                "400": {"description": "Invalid or expired OTP"}
            },
            "security": []
        }
    }

    spec["paths"]["/auth/refresh"] = {
        "post": {
            "summary": "Refresh access token",
            "description": "Exchange refresh token for new access token",
            "tags": ["runtime-auth"],
            "operationId": "refresh_token",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["refresh_token"],
                            "properties": {
                                "refresh_token": {"type": "string"}
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Token refreshed successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "access_token": {"type": "string"},
                                    "token_type": {"type": "string"},
                                    "expires_in": {"type": "integer"}
                                }
                            }
                        }
                    }
                },
                "401": {"description": "Invalid or expired refresh token"}
            },
            "security": []
        }
    }

    spec["paths"]["/auth/me"] = {
        "get": {
            "summary": "Get current user",
            "description": "Get authenticated user information",
            "tags": ["runtime-auth"],
            "operationId": "get_current_user",
            "responses": {
                "200": {
                    "description": "User information",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "format": "uuid"},
                                    "email": {"type": "string", "format": "email"},
                                    "last_login_at": {"type": "string", "format": "date-time"},
                                    "created_at": {"type": "string", "format": "date-time"}
                                }
                            }
                        }
                    }
                },
                "401": {"description": "Not authenticated"}
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        }
    }

    # Add states endpoints
    spec["paths"]["/states"] = {
        "get": {
            "summary": "List states",
            "description": "List all accessible state entries with optional filters",
            "tags": ["runtime-states"],
            "operationId": "list_states",
            "parameters": [
                {"name": "namespace", "in": "query", "schema": {"type": "string"}},
                {"name": "visibility", "in": "query", "schema": {"type": "string", "enum": ["private", "group", "public"]}},
                {"name": "skip", "in": "query", "schema": {"type": "integer", "default": 0}},
                {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 100}}
            ],
            "responses": {
                "200": {
                    "description": "List of states",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string", "format": "uuid"},
                                        "namespace": {"type": "string"},
                                        "key": {"type": "string"},
                                        "value": {"type": "object"},
                                        "visibility": {"type": "string"},
                                        "created_at": {"type": "string", "format": "date-time"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        },
        "post": {
            "summary": "Create state",
            "description": "Create new state entry for runtime storage",
            "tags": ["runtime-states"],
            "operationId": "create_state",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["namespace", "key", "value"],
                            "properties": {
                                "namespace": {"type": "string"},
                                "key": {"type": "string"},
                                "value": {"type": "object"},
                                "visibility": {"type": "string", "enum": ["private", "group", "public"], "default": "private"},
                                "group_id": {"type": "string", "format": "uuid"},
                                "description": {"type": "string"},
                                "tags": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "State created successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "format": "uuid"},
                                    "namespace": {"type": "string"},
                                    "key": {"type": "string"},
                                    "value": {"type": "object"}
                                }
                            }
                        }
                    }
                },
                "400": {"description": "Validation error"}
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        }
    }

    spec["paths"]["/states/{context_id}"] = {
        "get": {
            "summary": "Get state",
            "description": "Get specific state entry by ID",
            "tags": ["runtime-states"],
            "operationId": "get_state",
            "parameters": [
                {"name": "context_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}}
            ],
            "responses": {
                "200": {
                    "description": "State entry",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "format": "uuid"},
                                    "namespace": {"type": "string"},
                                    "key": {"type": "string"},
                                    "value": {"type": "object"}
                                }
                            }
                        }
                    }
                },
                "404": {"description": "State not found"}
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        },
        "put": {
            "summary": "Update state",
            "description": "Update existing state entry",
            "tags": ["runtime-states"],
            "operationId": "update_state",
            "parameters": [
                {"name": "context_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}}
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "object"},
                                "description": {"type": "string"},
                                "tags": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "State updated successfully"
                },
                "404": {"description": "State not found"}
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        },
        "delete": {
            "summary": "Delete state",
            "description": "Delete state entry",
            "tags": ["runtime-states"],
            "operationId": "delete_state",
            "parameters": [
                {"name": "context_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}}
            ],
            "responses": {
                "200": {
                    "description": "State deleted successfully"
                },
                "404": {"description": "State not found"}
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        }
    }

    # Add execution endpoints
    spec["paths"]["/executions"] = {
        "get": {
            "summary": "List executions",
            "description": "List function execution history for current user",
            "tags": ["runtime-executions"],
            "operationId": "list_executions",
            "parameters": [
                {"name": "skip", "in": "query", "schema": {"type": "integer", "default": 0}},
                {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 100}},
                {"name": "function_name", "in": "query", "schema": {"type": "string"}},
                {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["pending", "running", "completed", "failed", "awaiting_input"]}}
            ],
            "responses": {
                "200": {
                    "description": "List of executions",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "execution_id": {"type": "string"},
                                        "function_name": {"type": "string"},
                                        "status": {"type": "string"},
                                        "started_at": {"type": "string", "format": "date-time"},
                                        "completed_at": {"type": "string", "format": "date-time"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        }
    }

    spec["paths"]["/executions/{execution_id}"] = {
        "get": {
            "summary": "Get execution",
            "description": "Get specific execution details",
            "tags": ["runtime-executions"],
            "operationId": "get_execution",
            "parameters": [
                {"name": "execution_id", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "responses": {
                "200": {
                    "description": "Execution details",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "execution_id": {"type": "string"},
                                    "function_name": {"type": "string"},
                                    "status": {"type": "string"},
                                    "input_data": {"type": "object"},
                                    "output_data": {"type": "object"},
                                    "error_message": {"type": "string"},
                                    "started_at": {"type": "string", "format": "date-time"},
                                    "completed_at": {"type": "string", "format": "date-time"}
                                }
                            }
                        }
                    }
                },
                "404": {"description": "Execution not found"}
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        }
    }

    spec["paths"]["/executions/{execution_id}/steps"] = {
        "get": {
            "summary": "Get execution steps",
            "description": "Get all steps for an execution (function call tree)",
            "tags": ["runtime-executions"],
            "operationId": "get_execution_steps",
            "parameters": [
                {"name": "execution_id", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "responses": {
                "200": {
                    "description": "Execution steps",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "step_id": {"type": "string"},
                                        "function_name": {"type": "string"},
                                        "parent_step_id": {"type": "string"},
                                        "status": {"type": "string"},
                                        "started_at": {"type": "string", "format": "date-time"}
                                    }
                                }
                            }
                        }
                    }
                },
                "404": {"description": "Execution not found"}
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        }
    }

    spec["paths"]["/executions/{execution_id}/continue"] = {
        "post": {
            "summary": "Continue paused execution",
            "description": "Continue execution that is awaiting user input",
            "tags": ["runtime-executions"],
            "operationId": "continue_execution",
            "parameters": [
                {"name": "execution_id", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["input"],
                            "properties": {
                                "input": {"type": "object", "description": "User input to resume execution"}
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Execution continued",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "execution_id": {"type": "string"},
                                    "status": {"type": "string"},
                                    "output_data": {"type": "object"}
                                }
                            }
                        }
                    }
                },
                "400": {"description": "Execution not awaiting input"},
                "404": {"description": "Execution not found"}
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
        }
    }

    # Add health endpoint
    spec["paths"]["/health"] = {
        "get": {
            "summary": "Health check",
            "tags": ["system"],
            "operationId": "health_check",
            "responses": {
                "200": {
                    "description": "Service is healthy",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string", "example": "healthy"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    return spec
