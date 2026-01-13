"""
Configuration parser and validator
Validates declarative configuration before application
"""
from typing import List, Tuple, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import yaml

from app.schemas.config import SinasConfig


class ConfigValidationError:
    """Configuration validation error"""
    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message

    def __str__(self):
        return f"{self.path}: {self.message}"


class ConfigValidation:
    """Configuration validation result"""
    def __init__(self):
        self.errors: List[ConfigValidationError] = []
        self.warnings: List[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


class ConfigParser:
    """Parser and validator for SINAS configuration"""

    @staticmethod
    async def parse_and_validate(
        config_yaml: str,
        db: Optional[AsyncSession] = None,
        strict: bool = True
    ) -> Tuple[Optional[SinasConfig], ConfigValidation]:
        """
        Parse and validate SINAS configuration

        Args:
            config_yaml: YAML configuration string
            db: Optional database session for reference validation
            strict: If True, treat warnings as errors

        Returns:
            Tuple of (parsed config, validation result)
        """
        validation = ConfigValidation()

        # Parse YAML
        try:
            config_dict = yaml.safe_load(config_yaml)
        except yaml.YAMLError as e:
            validation.errors.append(
                ConfigValidationError("root", f"Invalid YAML: {str(e)}")
            )
            return None, validation

        # Parse into Pydantic model
        try:
            config = SinasConfig(**config_dict)
        except Exception as e:
            validation.errors.append(
                ConfigValidationError("root", f"Schema validation failed: {str(e)}")
            )
            return None, validation

        # Validate references
        await ConfigParser._validate_references(config, validation, db)

        return config, validation

    @staticmethod
    async def _validate_references(
        config: SinasConfig,
        validation: ConfigValidation,
        db: Optional[AsyncSession]
    ):
        """Validate cross-references within configuration"""
        errors = validation.errors
        spec = config.spec.model_dump() if hasattr(config.spec, 'model_dump') else config.spec.dict()

        # Collect all group names from config
        group_names = {g["name"] for g in spec.get("groups", [])}
        function_names = {f["name"] for f in spec.get("functions", [])}
        agent_names = {a["name"] for a in spec.get("agents", [])}
        llm_provider_names = {p["name"] for p in spec.get("llmProviders", [])}
        mcp_server_names = {s["name"] for s in spec.get("mcpServers", [])}

        # Database names (if db provided)
        db_group_names: Set[str] = set()
        db_function_names: Set[str] = set()
        db_agent_names: Set[str] = set()
        db_llm_provider_names: Set[str] = set()
        db_mcp_server_names: Set[str] = set()

        if db:
            from app.models.user import Group
            from app.models.function import Function
            from app.models.agent import Agent
            from app.models.llm_provider import LLMProvider
            from app.models.mcp import MCPServer

            # Load existing resource names from database
            result = await db.execute(select(Group.name))
            db_group_names = {name for (name,) in result.fetchall()}

            result = await db.execute(select(Function.name))
            db_function_names = {name for (name,) in result.fetchall()}

            result = await db.execute(select(Agent.name))
            db_agent_names = {name for (name,) in result.fetchall()}

            result = await db.execute(select(LLMProvider.name))
            db_llm_provider_names = {name for (name,) in result.fetchall()}

            result = await db.execute(select(MCPServer.name))
            db_mcp_server_names = {name for (name,) in result.fetchall()}

        # Combined sets (config + database)
        all_group_names = group_names | db_group_names
        all_function_names = function_names | db_function_names
        all_agent_names = agent_names | db_agent_names
        all_llm_provider_names = llm_provider_names | db_llm_provider_names
        all_mcp_server_names = mcp_server_names | db_mcp_server_names

        # Validate function references
        for i, func in enumerate(spec.get("functions", [])):
            if func["groupName"] not in all_group_names:
                errors.append(ConfigValidationError(
                    path=f"spec.functions[{i}].groupName",
                    message=f"Referenced group '{func['groupName']}' not defined"
                ))

        # Validate agent references
        for i, agent in enumerate(spec.get("agents", [])):
            if agent["groupName"] not in all_group_names:
                errors.append(ConfigValidationError(
                    path=f"spec.agents[{i}].groupName",
                    message=f"Referenced group '{agent['groupName']}' not defined"
                ))

            # Validate LLM provider reference
            if "llmProviderName" in agent and agent["llmProviderName"]:
                if agent["llmProviderName"] not in all_llm_provider_names:
                    errors.append(ConfigValidationError(
                        path=f"spec.agents[{i}].llmProviderName",
                        message=f"Referenced LLM provider '{agent['llmProviderName']}' not defined"
                    ))

            # Validate enabled function references
            if "enabledFunctions" in agent and agent["enabledFunctions"]:
                for func_name in agent["enabledFunctions"]:
                    if func_name not in all_function_names:
                        errors.append(ConfigValidationError(
                            path=f"spec.agents[{i}].enabledFunctions",
                            message=f"Referenced function '{func_name}' not defined"
                        ))

            # Validate enabled agent references (for agent calling)
            if "enabledAgents" in agent and agent["enabledAgents"]:
                for agent_name in agent["enabledAgents"]:
                    if agent_name not in all_agent_names and agent_name != agent["name"]:
                        errors.append(ConfigValidationError(
                            path=f"spec.agents[{i}].enabledAgents",
                            message=f"Referenced agent '{agent_name}' not defined"
                        ))

            # Validate MCP tool references
            if "enabledMcpTools" in agent and agent["enabledMcpTools"]:
                # Format: "server_name:tool_name"
                for tool_ref in agent["enabledMcpTools"]:
                    if ":" in tool_ref:
                        server_name = tool_ref.split(":")[0]
                        if server_name not in all_mcp_server_names:
                            errors.append(ConfigValidationError(
                                path=f"spec.agents[{i}].enabledMcpTools",
                                message=f"Referenced MCP server '{server_name}' not defined"
                            ))

        # Validate webhook references
        for i, webhook in enumerate(spec.get("webhooks", [])):
            if webhook["groupName"] not in all_group_names:
                errors.append(ConfigValidationError(
                    path=f"spec.webhooks[{i}].groupName",
                    message=f"Referenced group '{webhook['groupName']}' not defined"
                ))
            if webhook["functionName"] not in all_function_names:
                errors.append(ConfigValidationError(
                    path=f"spec.webhooks[{i}].functionName",
                    message=f"Referenced function '{webhook['functionName']}' not defined"
                ))

        # Validate schedule references
        for i, schedule in enumerate(spec.get("schedules", [])):
            if schedule["groupName"] not in all_group_names:
                errors.append(ConfigValidationError(
                    path=f"spec.schedules[{i}].groupName",
                    message=f"Referenced group '{schedule['groupName']}' not defined"
                ))
            if schedule["functionName"] not in all_function_names:
                errors.append(ConfigValidationError(
                    path=f"spec.schedules[{i}].functionName",
                    message=f"Referenced function '{schedule['functionName']}' not defined"
                ))

        # Validate MCP server references
        for i, server in enumerate(spec.get("mcpServers", [])):
            if server["groupName"] not in all_group_names:
                errors.append(ConfigValidationError(
                    path=f"spec.mcpServers[{i}].groupName",
                    message=f"Referenced group '{server['groupName']}' not defined"
                ))
