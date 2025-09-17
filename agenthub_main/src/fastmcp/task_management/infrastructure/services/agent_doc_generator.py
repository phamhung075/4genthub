import os
import yaml
from pathlib import Path
import shutil
import argparse
import subprocess
from typing import Optional, List
# Local path resolution function
def _find_project_root() -> Path:
    """Find project root by looking for agenthub_main directory"""
    current_path = Path(__file__).resolve()
    
    # Walk up the directory tree looking for agenthub_main
    while current_path.parent != current_path:
        if (current_path / "agenthub_main").exists():
            return current_path
        current_path = current_path.parent
    
    # If not found, use current working directory as fallback
    cwd = Path.cwd()
    if (cwd / "agenthub_main").exists():
        return cwd
        
    # Last resort - use the directory containing agenthub_main
    current_path = Path(__file__).resolve()
    while current_path.parent != current_path:
        if current_path.name == "agenthub_main":
            return current_path.parent
        current_path = current_path.parent
    
    # Absolute fallback
    # Use environment variable or default data path
    data_path = os.environ.get('AGENTHUB_DATA_PATH', '/data')
    # If running in development, try to find project root
    if not os.path.exists(data_path):
        # Try current working directory
        cwd = Path.cwd()
        if (cwd / "agenthub_main").exists():
            return cwd
        # Try parent directories
        current = Path(__file__).resolve()
        while current.parent != current:
            if (current / "agenthub_main").exists():
                return current
            current = current.parent
        # Fall back to temp directory for safety
        return Path("/tmp/agenthub_project")
    return Path(data_path)


class AgentDocGenerator:
    """Agent Documentation Generator for converting YAML agent definitions to MDC format
    
    The agent_yaml_lib and agents_output_dir can be set by:
    1. Passing them to the constructor
    2. Setting the AGENT_LIBRARY_DIR_PATH and AGENTS_OUTPUT_DIR environment variables
    3. Defaults to agent-library and .cursor/rules/agents under the project root
    """
    
    def __init__(self, agent_yaml_lib: Optional[Path] = None, agents_output_dir: Optional[Path] = None):
        project_root = _find_project_root()

        def resolve_path(path):
            p = Path(path)
            return p if p.is_absolute() else (project_root / p)

        env_yaml_lib = os.environ.get("AGENT_LIBRARY_DIR_PATH")
        env_agents_output = os.environ.get("AGENTS_OUTPUT_DIR")

        if agent_yaml_lib:
            self.agent_yaml_lib = resolve_path(agent_yaml_lib)
        elif env_yaml_lib:
            self.agent_yaml_lib = resolve_path(env_yaml_lib)
        else:
            # Handle project structure correctly - if project_root is agenthub_main itself,
            # agent-library is direct child, otherwise it's in agenthub_main subdirectory
            if project_root.name == "agenthub_main":
                self.agent_yaml_lib = project_root / "agent-library"
            else:
                self.agent_yaml_lib = project_root / "agenthub_main/agent-library"

        if agents_output_dir:
            self.agents_output_dir = resolve_path(agents_output_dir)
        elif env_agents_output:
            self.agents_output_dir = resolve_path(env_agents_output)
        else:
            self.agents_output_dir = project_root / ".cursor/rules/agents"

        self.project_root = project_root
        self.convert_script = self.agent_yaml_lib / "convert_yaml_to_mdc_format.py"
    
    def clear_agents_output_dir(self):
        """Clear all files in the agents output directory"""
        if self.agents_output_dir.exists() and self.agents_output_dir.is_dir():
            for file in self.agents_output_dir.iterdir():
                if file.is_file():
                    file.unlink()
    
    def convert_yaml_to_mdc(self, yaml_file: Path) -> str:
        """Convert a YAML file to MDC format by loading and dumping it."""
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return yaml.dump(data)
        except Exception as e:
            return f"(Error converting {yaml_file.name} to MDC: {e})"
    
    def generate_agent_docs(self, agent_name: Optional[str] = None, clear_all: bool = False):
        """Generate agent documentation for specified agent or all agents"""
        self.agents_output_dir.mkdir(parents=True, exist_ok=True)
        
        if clear_all:
            self.clear_agents_output_dir()
        
        agent_dirs = []
        if agent_name:
            target_dir = self.agent_yaml_lib / agent_name
            if target_dir.exists() and target_dir.is_dir():
                agent_dirs = [target_dir]
            else:
                print(f"Agent directory '{agent_name}' not found.")
                return
        else:
            agent_dirs = [d for d in self.agent_yaml_lib.iterdir() if d.is_dir() and d.name.endswith('_agent')]
        
        for agent_dir in agent_dirs:
            self._generate_single_agent_doc(agent_dir)
    
    def _generate_single_agent_doc(self, agent_dir: Path):
        """Generate documentation for a single agent"""
        job_desc_file = agent_dir / "job_desc.yaml"
        if not job_desc_file.exists():
            return
        
        try:
            with open(job_desc_file, 'r', encoding='utf-8') as f:
                job_desc = yaml.safe_load(f)
        except Exception as e:
            return
        
        # Compose markdown
        md_lines = [f"# {job_desc.get('name', agent_dir.name)}\n"]
        md_lines.append(f"**Slug:** `{job_desc.get('slug', agent_dir.name)}`  ")
        
        if 'role_definition' in job_desc:
            md_lines.append(f"**Role Definition:** {job_desc['role_definition']}  ")
        
        if 'when_to_use' in job_desc:
            md_lines.append(f"**When to Use:** {job_desc['when_to_use']}  ")
        
        if 'groups' in job_desc:
            md_lines.append(f"**Groups:** {', '.join(job_desc['groups'])}  ")
        
        md_lines.append("\n---\n")
        
        # Add more details from contexts, rules, tools, output_format if desired
        for subdir in ["contexts", "rules", "tools", "output_format"]:
            subdir_path = agent_dir / subdir
            if subdir_path.exists() and subdir_path.is_dir():
                md_lines.append(f"## {subdir.title()}\n")
                for file in subdir_path.glob("*.yaml"):
                    md_lines.append(f"### {file.stem}\n")
                    md_section = self.convert_yaml_to_mdc(file)
                    md_lines.append(md_section)
        
        # Write to .cursor/rules/agents/{agent_name}.mdc
        output_file = self.agents_output_dir / f"{agent_dir.name}.mdc"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))
    
    def generate_docs_for_assignees(self, assignees: Optional[List[str]], clear_all: bool = False):
        """Generate agent ai_docs for all unique assignees in the list."""
        if not assignees:
            return
            
        seen = set()
        for assignee in assignees:
            if assignee.startswith("@"):  # Remove '@' if present
                assignee_name = assignee[1:]
            else:
                assignee_name = assignee
            
            if not assignee_name.endswith("_agent"):
                agent_name = f"{assignee_name}_agent"
            else:
                agent_name = assignee_name
            
            if agent_name not in seen:
                self.generate_agent_docs(agent_name=agent_name, clear_all=clear_all)
                seen.add(agent_name)


# Always resolve relative to the project root
PROJECT_ROOT = _find_project_root()
# Handle project structure correctly - if project_root is agenthub_main itself,
# agent-library is direct child, otherwise it's in agenthub_main subdirectory
if PROJECT_ROOT.name == "agenthub_main":
    AGENT_YAML_LIB = PROJECT_ROOT / "agent-library"
else:
    AGENT_YAML_LIB = PROJECT_ROOT / "agenthub_main/agent-library"
AGENTS_OUTPUT_DIR = PROJECT_ROOT / ".cursor/rules/agents"
CONVERT_SCRIPT = AGENT_YAML_LIB / "convert_yaml_to_mdc_format.py"


def clear_agents_output_dir():
    generator = AgentDocGenerator(agents_output_dir=AGENTS_OUTPUT_DIR)
    generator.clear_agents_output_dir()


def convert_yaml_to_mdc(yaml_file: Path) -> str:
    generator = AgentDocGenerator()
    return generator.convert_yaml_to_mdc(yaml_file)


def generate_agent_docs(agent_name=None, clear_all=False):
    generator = AgentDocGenerator(
        agent_yaml_lib=AGENT_YAML_LIB, 
        agents_output_dir=AGENTS_OUTPUT_DIR
    )
    generator.generate_agent_docs(agent_name, clear_all)


def generate_docs_for_assignees(assignees, clear_all=False):
    """Generate agent ai_docs for all unique assignees in the list."""
    try:
        generator = AgentDocGenerator(
            agent_yaml_lib=AGENT_YAML_LIB,
            agents_output_dir=AGENTS_OUTPUT_DIR
        )
        generator.generate_docs_for_assignees(assignees, clear_all)
    except Exception as e:
        # Log error and continue gracefully - don't break task operations
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not generate agent ai_docs for assignees {assignees}: {e}")
        # Return silently to not break task operations


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate agent documentation.")
    parser.add_argument('--agent', type=str, help='Name of the agent directory (e.g., coding-agent)')
    parser.add_argument('--clear-all', action='store_true', help='Clear all agent ai_docs before generating')
    args = parser.parse_args()
    generate_agent_docs(agent_name=args.agent, clear_all=args.clear_all) 