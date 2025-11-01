"""
YAML Agent Template Loader Service

This service loads agent templates from the agent-library YAML files
and converts them into AgentTemplate domain entities.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ...domain.entities.agent_template import AgentTemplate
from ...domain.value_objects.agent_template_id import AgentTemplateId
from ...domain.value_objects.agent_configuration import AgentConfiguration

logger = logging.getLogger(__name__)


class YAMLAgentTemplateLoader:
    """Loads agent templates from agent-library YAML files"""

    def __init__(self, agent_library_path: str):
        """
        Initialize the loader with agent-library base path

        Args:
            agent_library_path: Path to agent-library directory
        """
        self.agent_library_path = Path(agent_library_path)
        self.agents_path = self.agent_library_path / "agents"

        if not self.agents_path.exists():
            raise ValueError(f"Agent library path not found: {self.agents_path}")

    def load_all_agents(self) -> List[AgentTemplate]:
        """
        Load all agent templates from the agent-library

        Returns:
            List of AgentTemplate entities
        """
        templates = []

        # Get all agent directories
        agent_dirs = [d for d in self.agents_path.iterdir() if d.is_dir()]

        logger.info(f"Found {len(agent_dirs)} agent directories in agent-library")

        for agent_dir in agent_dirs:
            try:
                template = self.load_agent(agent_dir)
                templates.append(template)
                logger.info(f"✅ Loaded agent: {template.slug}")
            except Exception as e:
                logger.error(f"❌ Failed to load agent from {agent_dir.name}: {e}")
                continue

        logger.info(f"Successfully loaded {len(templates)} agent templates")
        return templates

    def load_agent(self, agent_dir: Path) -> AgentTemplate:
        """
        Load a single agent template from its directory

        Args:
            agent_dir: Path to the agent directory

        Returns:
            AgentTemplate entity
        """
        # 1. Load config.yaml for basic agent info
        config_data = self._load_yaml(agent_dir / "config.yaml")
        agent_info = config_data.get("agent_info", {})

        # 2. Load capabilities.yaml for tools and capabilities
        capabilities_data = self._load_yaml(agent_dir / "capabilities.yaml")

        # 3. Load system prompt from contexts/{slug}_instructions.yaml
        slug = agent_info.get("slug")
        # Convert hyphenated slug to underscored for file naming convention
        slug_underscored = slug.replace("-", "_")
        instructions_file = agent_dir / "contexts" / f"{slug_underscored}_instructions.yaml"
        instructions_data = self._load_yaml(instructions_file)
        system_prompt = instructions_data.get("custom_instructions", "")

        # 4. Load all rules from rules/*.yaml
        rules = self._load_rules(agent_dir / "rules")

        # 5. Load output format from output_format/output_specification.yaml
        output_format_file = agent_dir / "output_format" / "output_specification.yaml"
        output_format = None
        if output_format_file.exists():
            output_format_data = self._load_yaml(output_format_file)
            output_format = output_format_data.get("output_specification")

        # 6. Load metadata.yaml (multi-document YAML file)
        metadata_data = self._load_yaml(agent_dir / "metadata.yaml", multi_document=True)

        # 7. Extract tools from capabilities
        tools = self._extract_tools(capabilities_data)

        # 8. Build capabilities object (structured for AgentConfiguration)
        capabilities_obj = self._build_capabilities_object(capabilities_data)

        # 9. Create AgentConfiguration value object
        configuration = AgentConfiguration(
            system_prompt=system_prompt,
            tools=tools,
            capabilities=capabilities_obj,
            rules=rules,
            output_format=output_format,
            metadata=metadata_data
        )

        # 10. Create AgentTemplate entity
        template = AgentTemplate(
            id=AgentTemplateId.generate_new(),
            slug=slug,
            name=agent_info.get("name", slug),
            description=agent_info.get("description", ""),
            category=agent_info.get("category", "general"),
            version=agent_info.get("version", "1.0.0"),
            default_configuration=configuration,
            metadata={
                "source": "agent-library",
                "migration_date": agent_info.get("migration_date"),
                "usage_scenarios": agent_info.get("usage_scenarios"),
                "author": agent_info.get("author", "agenthub"),
                **metadata_data
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        return template

    def _load_yaml(self, file_path: Path, multi_document: bool = False) -> Dict[str, Any]:
        """
        Load and parse a YAML file

        Args:
            file_path: Path to YAML file
            multi_document: If True, handle multiple YAML documents (separated by ---)

        Returns:
            Parsed YAML data as dictionary
        """
        if not file_path.exists():
            logger.warning(f"YAML file not found: {file_path}")
            return {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if multi_document:
                    # Load all documents and return the first one (metadata.yaml case)
                    docs = list(yaml.safe_load_all(f))
                    data = docs[0] if docs else {}
                else:
                    data = yaml.safe_load(f)
                return data if data is not None else {}
        except Exception as e:
            logger.error(f"Error loading YAML file {file_path}: {e}")
            return {}

    def _load_rules(self, rules_dir: Path) -> Optional[List[str]]:
        """
        Load all rules from rules/*.yaml files

        Args:
            rules_dir: Path to rules directory

        Returns:
            List of rule descriptions or None
        """
        if not rules_dir.exists():
            return None

        rules = []
        rule_files = sorted(rules_dir.glob("*.yaml"))

        for rule_file in rule_files:
            try:
                rule_data = self._load_yaml(rule_file)
                # Extract rule content (structure varies, so we take the whole dict)
                rule_name = rule_file.stem
                rules.append({
                    "name": rule_name,
                    "content": rule_data
                })
            except Exception as e:
                logger.error(f"Error loading rule file {rule_file}: {e}")
                continue

        return rules if rules else None

    def _extract_tools(self, capabilities_data: Dict[str, Any]) -> List[str]:
        """
        Extract MCP tools list from capabilities.yaml

        Args:
            capabilities_data: Parsed capabilities.yaml

        Returns:
            List of tool names
        """
        mcp_tools = capabilities_data.get("mcp_tools", {})
        if isinstance(mcp_tools, dict):
            tools = mcp_tools.get("tools", [])
            return tools if isinstance(tools, list) else []
        return []

    def _build_capabilities_object(self, capabilities_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build structured capabilities object from capabilities.yaml

        Args:
            capabilities_data: Parsed capabilities.yaml

        Returns:
            Structured capabilities dictionary
        """
        return {
            "file_operations": capabilities_data.get("file_operations", {}),
            "command_execution": capabilities_data.get("command_execution", {}),
            "mcp_tools": capabilities_data.get("mcp_tools", {}),
            "collaboration": capabilities_data.get("collaboration", {})
        }
