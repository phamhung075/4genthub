"""
Context Templates and Presets System

Provides reusable context templates for common project patterns,
enabling quick setup and standardization across projects.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from datetime import datetime

from ...domain.models.unified_context import ContextLevel
from ..services.unified_context_service import UnifiedContextService

logger = logging.getLogger(__name__)


class TemplateCategory(Enum):
    """Template categories"""
    WEB_APP = "web_app"
    API_SERVICE = "api_service"
    MOBILE_APP = "mobile_app"
    MICROSERVICE = "microservice"
    DATA_PIPELINE = "data_pipeline"
    ML_MODEL = "ml_model"
    CLI_TOOL = "cli_tool"
    LIBRARY = "library"
    CUSTOM = "custom"


@dataclass
class TemplateVariable:
    """Variable that can be customized in a template"""
    name: str
    description: str
    default_value: Any
    required: bool = False
    validation_regex: Optional[str] = None


@dataclass
class ContextTemplate:
    """Reusable context template"""
    id: str
    name: str
    description: str
    category: TemplateCategory
    level: ContextLevel
    
    # Template data structure
    data_template: Dict[str, Any]
    
    # Template metadata (required fields first)
    author: str
    
    # Variables that can be customized
    variables: List[TemplateVariable] = field(default_factory=list)
    
    # Template metadata (optional fields)
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Usage statistics
    usage_count: int = 0
    last_used_at: Optional[datetime] = None


class TemplateRegistry:
    """Registry of available context templates"""
    
    def __init__(self):
        self.templates: Dict[str, ContextTemplate] = {}
        self._load_builtin_templates()
    
    def _load_builtin_templates(self):
        """Load built-in templates"""
        
        # Web Application Template
        self.register(ContextTemplate(
            id="web_app_react",
            name="React Web Application",
            description="Standard React application with TypeScript",
            category=TemplateCategory.WEB_APP,
            level=ContextLevel.PROJECT,
            data_template={
                "project_type": "web_application",
                "framework": "React",
                "language": "TypeScript",
                "build_tool": "Vite",
                "testing": {
                    "unit": "Vitest",
                    "e2e": "Playwright",
                    "coverage_threshold": "{{coverage_threshold}}"
                },
                "dependencies": {
                    "ui_library": "{{ui_library}}",
                    "state_management": "{{state_management}}",
                    "routing": "React Router",
                    "styling": "{{styling_solution}}"
                },
                "structure": {
                    "src/": "Source code",
                    "src/components/": "React components",
                    "src/hooks/": "Custom hooks",
                    "src/services/": "API services",
                    "src/utils/": "Utilities",
                    "src/types/": "TypeScript types",
                    "tests/": "Test files"
                },
                "conventions": {
                    "naming": "PascalCase for components, camelCase for functions",
                    "file_structure": "Feature-based organization",
                    "state_management": "{{state_pattern}}"
                },
                "ci_cd": {
                    "pipeline": "GitHub Actions",
                    "deployment": "{{deployment_platform}}"
                }
            },
            variables=[
                TemplateVariable(
                    name="coverage_threshold",
                    description="Minimum test coverage percentage",
                    default_value=80,
                    required=False
                ),
                TemplateVariable(
                    name="ui_library",
                    description="UI component library",
                    default_value="shadcn/ui",
                    required=False
                ),
                TemplateVariable(
                    name="state_management",
                    description="State management solution",
                    default_value="Zustand",
                    required=False
                ),
                TemplateVariable(
                    name="styling_solution",
                    description="CSS solution",
                    default_value="Tailwind CSS",
                    required=False
                ),
                TemplateVariable(
                    name="state_pattern",
                    description="State management pattern",
                    default_value="Context + Hooks",
                    required=False
                ),
                TemplateVariable(
                    name="deployment_platform",
                    description="Deployment platform",
                    default_value="Vercel",
                    required=False
                )
            ],
            tags=["frontend", "react", "typescript", "spa"]
        ))
        
        # API Service Template
        self.register(ContextTemplate(
            id="api_fastapi",
            name="FastAPI Service",
            description="RESTful API service with FastAPI",
            category=TemplateCategory.API_SERVICE,
            level=ContextLevel.PROJECT,
            data_template={
                "project_type": "api_service",
                "framework": "FastAPI",
                "language": "Python",
                "database": {
                    "type": "{{database_type}}",
                    "orm": "SQLAlchemy",
                    "migrations": "Alembic"
                },
                "authentication": {
                    "type": "{{auth_type}}",
                    "token_type": "JWT",
                    "provider": "{{auth_provider}}"
                },
                "structure": {
                    "src/": "Source code",
                    "src/api/": "API endpoints",
                    "src/models/": "Database models",
                    "src/services/": "Business logic",
                    "src/schemas/": "Pydantic schemas",
                    "src/utils/": "Utilities",
                    "tests/": "Test files"
                },
                "testing": {
                    "framework": "pytest",
                    "coverage": "{{coverage_threshold}}%"
                },
                "documentation": {
                    "openapi": "Auto-generated",
                    "redoc": "Enabled"
                },
                "deployment": {
                    "containerization": "Docker",
                    "orchestration": "{{orchestration}}",
                    "monitoring": "{{monitoring_solution}}"
                }
            },
            variables=[
                TemplateVariable(
                    name="database_type",
                    description="Database system",
                    default_value="PostgreSQL",
                    required=True
                ),
                TemplateVariable(
                    name="auth_type",
                    description="Authentication type",
                    default_value="OAuth2",
                    required=False
                ),
                TemplateVariable(
                    name="auth_provider",
                    description="Auth provider",
                    default_value="Internal",
                    required=False
                ),
                TemplateVariable(
                    name="coverage_threshold",
                    description="Test coverage threshold",
                    default_value=85,
                    required=False
                ),
                TemplateVariable(
                    name="orchestration",
                    description="Container orchestration",
                    default_value="Kubernetes",
                    required=False
                ),
                TemplateVariable(
                    name="monitoring_solution",
                    description="Monitoring solution",
                    default_value="Prometheus + Grafana",
                    required=False
                )
            ],
            tags=["backend", "api", "python", "fastapi"]
        ))
        
        # Machine Learning Model Template
        self.register(ContextTemplate(
            id="ml_model_training",
            name="ML Model Training Pipeline",
            description="Machine learning model training and deployment",
            category=TemplateCategory.ML_MODEL,
            level=ContextLevel.PROJECT,
            data_template={
                "project_type": "ml_model",
                "framework": "{{ml_framework}}",
                "language": "Python",
                "model_type": "{{model_type}}",
                "data": {
                    "source": "{{data_source}}",
                    "preprocessing": "{{preprocessing_pipeline}}",
                    "validation_split": 0.2,
                    "test_split": 0.1
                },
                "training": {
                    "epochs": "{{epochs}}",
                    "batch_size": "{{batch_size}}",
                    "optimizer": "{{optimizer}}",
                    "loss_function": "{{loss_function}}",
                    "metrics": ["accuracy", "precision", "recall"]
                },
                "experiment_tracking": {
                    "tool": "{{tracking_tool}}",
                    "artifacts": ["model", "metrics", "plots"]
                },
                "deployment": {
                    "serving": "{{serving_platform}}",
                    "api": "REST",
                    "monitoring": "Model performance tracking"
                },
                "structure": {
                    "data/": "Dataset storage",
                    "notebooks/": "Exploration notebooks",
                    "src/": "Training code",
                    "models/": "Saved models",
                    "configs/": "Configuration files",
                    "tests/": "Model tests"
                }
            },
            variables=[
                TemplateVariable(
                    name="ml_framework",
                    description="ML framework",
                    default_value="PyTorch",
                    required=True
                ),
                TemplateVariable(
                    name="model_type",
                    description="Type of model",
                    default_value="Classification",
                    required=True
                ),
                TemplateVariable(
                    name="data_source",
                    description="Data source location",
                    default_value="S3",
                    required=False
                ),
                TemplateVariable(
                    name="preprocessing_pipeline",
                    description="Data preprocessing",
                    default_value="StandardScaler + PCA",
                    required=False
                ),
                TemplateVariable(
                    name="epochs",
                    description="Training epochs",
                    default_value=100,
                    required=False
                ),
                TemplateVariable(
                    name="batch_size",
                    description="Batch size",
                    default_value=32,
                    required=False
                ),
                TemplateVariable(
                    name="optimizer",
                    description="Optimizer",
                    default_value="Adam",
                    required=False
                ),
                TemplateVariable(
                    name="loss_function",
                    description="Loss function",
                    default_value="CrossEntropy",
                    required=False
                ),
                TemplateVariable(
                    name="tracking_tool",
                    description="Experiment tracking tool",
                    default_value="MLflow",
                    required=False
                ),
                TemplateVariable(
                    name="serving_platform",
                    description="Model serving platform",
                    default_value="TorchServe",
                    required=False
                )
            ],
            tags=["ml", "ai", "pytorch", "training"]
        ))
        
        # Task Template for Feature Implementation
        self.register(ContextTemplate(
            id="task_feature_impl",
            name="Feature Implementation Task",
            description="Standard template for implementing a new feature",
            category=TemplateCategory.CUSTOM,
            level=ContextLevel.TASK,
            data_template={
                "task_type": "feature_implementation",
                "requirements": {
                    "functional": "{{functional_requirements}}",
                    "non_functional": "{{non_functional_requirements}}",
                    "acceptance_criteria": []
                },
                "technical_approach": {
                    "architecture": "{{architecture_pattern}}",
                    "technologies": [],
                    "dependencies": []
                },
                "implementation_plan": {
                    "phases": [
                        "Design",
                        "Implementation",
                        "Testing",
                        "Documentation",
                        "Review"
                    ],
                    "estimated_effort": "{{effort_estimate}}"
                },
                "testing_strategy": {
                    "unit_tests": True,
                    "integration_tests": True,
                    "e2e_tests": "{{e2e_required}}",
                    "performance_tests": "{{perf_required}}"
                },
                "documentation": {
                    "api_docs": True,
                    "user_guide": "{{user_guide_required}}",
                    "technical_docs": True
                },
                "review_checklist": [
                    "Code quality",
                    "Test coverage",
                    "Documentation",
                    "Security review",
                    "Performance impact"
                ]
            },
            variables=[
                TemplateVariable(
                    name="functional_requirements",
                    description="Functional requirements",
                    default_value="To be defined",
                    required=True
                ),
                TemplateVariable(
                    name="non_functional_requirements",
                    description="Non-functional requirements",
                    default_value="Performance, Security, Scalability",
                    required=False
                ),
                TemplateVariable(
                    name="architecture_pattern",
                    description="Architecture pattern",
                    default_value="MVC",
                    required=False
                ),
                TemplateVariable(
                    name="effort_estimate",
                    description="Effort estimate",
                    default_value="3 days",
                    required=False
                ),
                TemplateVariable(
                    name="e2e_required",
                    description="E2E tests required",
                    default_value=True,
                    required=False
                ),
                TemplateVariable(
                    name="perf_required",
                    description="Performance tests required",
                    default_value=False,
                    required=False
                ),
                TemplateVariable(
                    name="user_guide_required",
                    description="User guide required",
                    default_value=True,
                    required=False
                )
            ],
            tags=["task", "feature", "planning"]
        ))
    
    def register(self, template: ContextTemplate) -> None:
        """Register a new template"""
        self.templates[template.id] = template
        logger.info(f"Registered template: {template.id}")
    
    def get(self, template_id: str) -> Optional[ContextTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def list_by_category(self, category: TemplateCategory) -> List[ContextTemplate]:
        """List templates by category"""
        return [
            t for t in self.templates.values() 
            if t.category == category
        ]
    
    def list_by_level(self, level: ContextLevel) -> List[ContextTemplate]:
        """List templates by context level"""
        return [
            t for t in self.templates.values() 
            if t.level == level
        ]
    
    def search_by_tags(self, tags: List[str]) -> List[ContextTemplate]:
        """Search templates by tags"""
        results = []
        for template in self.templates.values():
            if any(tag in template.tags for tag in tags):
                results.append(template)
        return results


class ContextTemplateService:
    """
    Service for managing and applying context templates.
    """
    
    def __init__(self, context_service: UnifiedContextService):
        self.context_service = context_service
        self.registry = TemplateRegistry()
    
    def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        level: Optional[ContextLevel] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """List available templates"""
        
        templates = list(self.registry.templates.values())
        
        # Filter by category
        if category:
            templates = [t for t in templates if t.category == category]
        
        # Filter by level
        if level:
            templates = [t for t in templates if t.level == level]
        
        # Filter by tags
        if tags:
            templates = [
                t for t in templates 
                if any(tag in t.tags for tag in tags)
            ]
        
        # Convert to dict format
        return [self._template_to_dict(t) for t in templates]
    
    def _template_to_dict(self, template: ContextTemplate) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'category': template.category.value,
            'level': template.level.value,
            'tags': template.tags,
            'variables': [
                {
                    'name': v.name,
                    'description': v.description,
                    'default': v.default_value,
                    'required': v.required
                }
                for v in template.variables
            ],
            'usage_count': template.usage_count,
            'version': template.version
        }
    
    async def apply_template(
        self,
        template_id: str,
        context_id: str,
        user_id: str,
        variables: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        git_branch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply a template to create a new context.
        
        Args:
            template_id: Template to use
            context_id: ID for the new context
            user_id: User creating the context
            variables: Variable values to customize template
            project_id: Project ID (for project/branch/task levels)
            git_branch_id: Branch ID (for branch/task levels)
        
        Returns:
            Created context data
        """
        
        # Get template
        template = self.registry.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Apply variables to template
        context_data = self._apply_variables(
            template=template,
            variables=variables or {}
        )
        
        # Add template metadata
        context_data['_template'] = {
            'id': template.id,
            'name': template.name,
            'version': template.version,
            'applied_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Create context from template
        result = await self.context_service.create_context(
            context_level=template.level,
            context_id=context_id,
            data=context_data,
            user_id=user_id,
            project_id=project_id,
            git_branch_id=git_branch_id
        )
        
        # Update template usage statistics
        template.usage_count += 1
        template.last_used_at = datetime.now(timezone.utc)
        
        return result
    
    def _apply_variables(
        self,
        template: ContextTemplate,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply variables to template data"""
        
        # Convert template to JSON string
        template_str = json.dumps(template.data_template)
        
        # Apply each variable
        for var in template.variables:
            # Get value (use provided or default)
            value = variables.get(var.name, var.default_value)
            
            # Validate required variables
            if var.required and var.name not in variables:
                raise ValueError(f"Required variable not provided: {var.name}")
            
            # Replace placeholder
            placeholder = f"{{{{{var.name}}}}}"
            if isinstance(value, str):
                template_str = template_str.replace(placeholder, value)
            else:
                template_str = template_str.replace(f'"{placeholder}"', json.dumps(value))
        
        # Parse back to dict
        return json.loads(template_str)
    
    def create_custom_template(
        self,
        name: str,
        description: str,
        level: ContextLevel,
        data_template: Dict[str, Any],
        variables: Optional[List[TemplateVariable]] = None,
        tags: Optional[List[str]] = None
    ) -> ContextTemplate:
        """Create a custom template"""
        
        import uuid
        
        template = ContextTemplate(
            id=f"custom_{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            category=TemplateCategory.CUSTOM,
            level=level,
            data_template=data_template,
            variables=variables or [],
            tags=tags or [],
            author="user"
        )
        
        self.registry.register(template)
        return template
    
    def export_template(self, template_id: str) -> str:
        """Export template as JSON"""
        
        template = self.registry.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        export_data = {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'category': template.category.value,
            'level': template.level.value,
            'data_template': template.data_template,
            'variables': [
                {
                    'name': v.name,
                    'description': v.description,
                    'default_value': v.default_value,
                    'required': v.required,
                    'validation_regex': v.validation_regex
                }
                for v in template.variables
            ],
            'tags': template.tags,
            'version': template.version,
            'author': template.author
        }
        
        return json.dumps(export_data, indent=2)
    
    def import_template(self, json_str: str) -> ContextTemplate:
        """Import template from JSON"""
        
        data = json.loads(json_str)
        
        # Create template from import data
        template = ContextTemplate(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            category=TemplateCategory(data['category']),
            level=ContextLevel(data['level']),
            data_template=data['data_template'],
            variables=[
                TemplateVariable(
                    name=v['name'],
                    description=v['description'],
                    default_value=v['default_value'],
                    required=v.get('required', False),
                    validation_regex=v.get('validation_regex')
                )
                for v in data.get('variables', [])
            ],
            tags=data.get('tags', []),
            version=data.get('version', '1.0.0'),
            author=data.get('author', 'imported')
        )
        
        self.registry.register(template)
        return template