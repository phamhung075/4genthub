"""
ML Dependency Predictor - Infrastructure service for machine learning predictions

This service provides the infrastructure layer for ML-based dependency prediction,
including model persistence, training data management, and prediction serving.
"""

import logging
import json
import pickle
import os
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path

from fastmcp.task_management.domain.services.intelligence.pattern_recognition_engine import (
    PatternRecognitionEngine, PatternPrediction, DependencyPattern
)
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class MLModelPersistence:
    """Handles persistence of ML models and training data"""
    
    def __init__(self, model_dir: str = "models/dependency_prediction"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def save_patterns(self, patterns: Dict[str, DependencyPattern], model_version: str = "latest") -> str:
        """Save learned patterns to disk"""
        try:
            patterns_file = self.model_dir / f"patterns_{model_version}.json"
            
            # Convert patterns to serializable format
            serializable_patterns = {}
            for pattern_id, pattern in patterns.items():
                pattern_dict = asdict(pattern)
                # Convert datetime objects to strings
                pattern_dict['created_at'] = pattern.created_at.isoformat()
                pattern_dict['last_updated'] = pattern.last_updated.isoformat()
                pattern_dict['pattern_type'] = pattern.pattern_type.value
                serializable_patterns[pattern_id] = pattern_dict
            
            # Save to file
            with open(patterns_file, 'w') as f:
                json.dump(serializable_patterns, f, indent=2)
            
            # Save metadata
            metadata = {
                'model_version': model_version,
                'pattern_count': len(patterns),
                'saved_at': datetime.now(timezone.utc).isoformat(),
                'file_size': patterns_file.stat().st_size
            }
            
            metadata_file = self.model_dir / f"metadata_{model_version}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Saved {len(patterns)} patterns to {patterns_file}")
            return str(patterns_file)
            
        except Exception as e:
            self.logger.error(f"Error saving patterns: {e}")
            raise
    
    def load_patterns(self, model_version: str = "latest") -> Dict[str, DependencyPattern]:
        """Load learned patterns from disk"""
        try:
            patterns_file = self.model_dir / f"patterns_{model_version}.json"
            
            if not patterns_file.exists():
                self.logger.warning(f"Pattern file {patterns_file} does not exist")
                return {}
            
            with open(patterns_file, 'r') as f:
                pattern_data = json.load(f)
            
            # Convert back to DependencyPattern objects
            patterns = {}
            for pattern_id, pattern_dict in pattern_data.items():
                # Convert strings back to datetime objects
                pattern_dict['created_at'] = datetime.fromisoformat(pattern_dict['created_at'])
                pattern_dict['last_updated'] = datetime.fromisoformat(pattern_dict['last_updated'])
                
                # Convert pattern type back to enum
                from fastmcp.task_management.domain.services.intelligence.pattern_recognition_engine import PatternType
                pattern_dict['pattern_type'] = PatternType(pattern_dict['pattern_type'])
                
                pattern = DependencyPattern(**pattern_dict)
                patterns[pattern_id] = pattern
            
            self.logger.info(f"Loaded {len(patterns)} patterns from {patterns_file}")
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error loading patterns: {e}")
            return {}
    
    def get_available_versions(self) -> List[str]:
        """Get list of available model versions"""
        try:
            versions = []
            for file_path in self.model_dir.glob("patterns_*.json"):
                version = file_path.stem.replace("patterns_", "")
                versions.append(version)
            
            return sorted(versions, reverse=True)  # Most recent first
            
        except Exception as e:
            self.logger.error(f"Error getting available versions: {e}")
            return []
    
    def cleanup_old_versions(self, keep_versions: int = 5):
        """Clean up old model versions, keeping only the most recent ones"""
        try:
            versions = self.get_available_versions()
            if len(versions) <= keep_versions:
                return
            
            versions_to_delete = versions[keep_versions:]
            deleted_count = 0
            
            for version in versions_to_delete:
                pattern_file = self.model_dir / f"patterns_{version}.json"
                metadata_file = self.model_dir / f"metadata_{version}.json"
                
                if pattern_file.exists():
                    pattern_file.unlink()
                    deleted_count += 1
                
                if metadata_file.exists():
                    metadata_file.unlink()
            
            self.logger.info(f"Cleaned up {deleted_count} old model versions")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old versions: {e}")


class TrainingDataCollector:
    """Collects and prepares training data from the task repository"""
    
    def __init__(self, task_repository: TaskRepository):
        self.task_repository = task_repository
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def collect_project_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Collect historical project data for training
        
        Args:
            limit: Maximum number of projects to collect (None for all)
            
        Returns:
            List of project data with tasks and dependencies
        """
        try:
            # For this implementation, we'll simulate collecting from the repository
            # In a real implementation, this would query completed projects with dependencies
            
            projects = []
            all_tasks = self.task_repository.find_all()
            
            if not all_tasks:
                self.logger.warning("No tasks found for training data collection")
                return []
            
            # Group tasks by project (using git_branch_id as project indicator)
            projects_by_branch = {}
            for task in all_tasks:
                branch_id = getattr(task, 'git_branch_id', 'unknown')
                if branch_id not in projects_by_branch:
                    projects_by_branch[branch_id] = []
                projects_by_branch[branch_id].append(task)
            
            for branch_id, branch_tasks in projects_by_branch.items():
                if len(branch_tasks) < 2:  # Need at least 2 tasks for meaningful patterns
                    continue
                
                project_data = self._create_project_data(branch_id, branch_tasks)
                if project_data:
                    projects.append(project_data)
                
                if limit and len(projects) >= limit:
                    break
            
            self.logger.info(f"Collected {len(projects)} projects for training")
            return projects
            
        except Exception as e:
            self.logger.error(f"Error collecting training data: {e}")
            return []
    
    def _create_project_data(self, branch_id: str, tasks: List) -> Optional[Dict[str, Any]]:
        """Create project data structure from tasks"""
        try:
            task_data = []
            
            for task in tasks:
                # Convert task to dictionary format
                task_dict = {
                    'id': str(task.id),
                    'title': task.title,
                    'description': task.description or "",
                    'details': task.details or "",
                    'assignees': task.assignees if task.assignees else [],
                    'priority': task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
                    'status': task.status.value if hasattr(task.status, 'value') else str(task.status),
                    'estimated_effort': task.estimated_effort or "",
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'updated_at': task.updated_at.isoformat() if task.updated_at else None,
                    'dependencies': task.get_dependency_ids() if hasattr(task, 'get_dependency_ids') else []
                }
                task_data.append(task_dict)
            
            # Only include projects with some dependencies
            total_deps = sum(len(task['dependencies']) for task in task_data)
            if total_deps == 0:
                return None
            
            project_data = {
                'id': branch_id,
                'domain': self._infer_project_domain(task_data),
                'task_count': len(task_data),
                'dependency_count': total_deps,
                'tasks': task_data,
                'collected_at': datetime.now(timezone.utc).isoformat()
            }
            
            return project_data
            
        except Exception as e:
            self.logger.error(f"Error creating project data for branch {branch_id}: {e}")
            return None
    
    def _infer_project_domain(self, task_data: List[Dict[str, Any]]) -> str:
        """Infer project domain from task content"""
        domain_indicators = {
            'web': ['frontend', 'backend', 'api', 'html', 'css', 'javascript', 'react', 'vue'],
            'mobile': ['android', 'ios', 'mobile', 'app', 'flutter', 'react native'],
            'data': ['database', 'sql', 'analytics', 'etl', 'data', 'ml', 'ai'],
            'devops': ['docker', 'kubernetes', 'ci', 'cd', 'deployment', 'infrastructure'],
            'testing': ['test', 'qa', 'automation', 'selenium', 'cypress', 'junit']
        }
        
        domain_scores = {domain: 0 for domain in domain_indicators}
        
        for task in task_data:
            content = f"{task['title']} {task['description']} {task['details']}".lower()
            
            for domain, indicators in domain_indicators.items():
                for indicator in indicators:
                    if indicator in content:
                        domain_scores[domain] += 1
        
        # Return domain with highest score, or 'general' if no clear domain
        max_domain = max(domain_scores, key=domain_scores.get)
        return max_domain if domain_scores[max_domain] > 0 else 'general'


class MLDependencyPredictor:
    """
    Infrastructure service for ML-based dependency prediction
    
    This service orchestrates the ML pipeline for dependency prediction including
    training data collection, model training, persistence, and prediction serving.
    """
    
    def __init__(self, task_repository: TaskRepository, model_dir: str = "models/dependency_prediction"):
        self.task_repository = task_repository
        self.persistence = MLModelPersistence(model_dir)
        self.data_collector = TrainingDataCollector(task_repository)
        self.pattern_engine = PatternRecognitionEngine()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Try to load existing model
        self._load_latest_model()
    
    def _load_latest_model(self):
        """Load the latest trained model if available"""
        try:
            versions = self.persistence.get_available_versions()
            if versions:
                latest_version = versions[0]
                patterns = self.persistence.load_patterns(latest_version)
                if patterns:
                    self.pattern_engine.patterns = patterns
                    self.pattern_engine.trained = True
                    self.logger.info(f"Loaded model version {latest_version} with {len(patterns)} patterns")
        except Exception as e:
            self.logger.error(f"Error loading latest model: {e}")
    
    def train_model(self, project_limit: Optional[int] = None, save_model: bool = True) -> Dict[str, Any]:
        """
        Train the dependency prediction model
        
        Args:
            project_limit: Maximum number of projects to use for training
            save_model: Whether to save the trained model to disk
            
        Returns:
            Training results and statistics
        """
        self.logger.info("Starting model training")
        
        try:
            # Collect training data
            training_data = self.data_collector.collect_project_history(project_limit)
            
            if not training_data:
                return {
                    'status': 'failed',
                    'error': 'No training data available',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Train the pattern recognition engine
            training_results = self.pattern_engine.train_from_historical_data(training_data)
            
            # Save model if requested
            if save_model and self.pattern_engine.patterns:
                model_version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                model_path = self.persistence.save_patterns(
                    self.pattern_engine.patterns, 
                    model_version
                )
                training_results['model_saved'] = model_path
                training_results['model_version'] = model_version
                
                # Clean up old versions
                self.persistence.cleanup_old_versions(keep_versions=5)
            
            training_results['status'] = 'completed'
            training_results['training_data_projects'] = len(training_data)
            
            self.logger.info(f"Model training completed: {training_results}")
            return training_results
            
        except Exception as e:
            error_msg = f"Error training model: {e}"
            self.logger.error(error_msg)
            return {
                'status': 'failed',
                'error': error_msg,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def predict_dependencies(self, task, candidate_tasks: List) -> List[PatternPrediction]:
        """
        Predict dependencies for a task using trained ML models
        
        Args:
            task: Task to predict dependencies for
            candidate_tasks: List of potential dependency tasks
            
        Returns:
            List of dependency predictions with confidence scores
        """
        if not self.pattern_engine.trained:
            self.logger.warning("Model not trained, cannot make predictions")
            return []
        
        try:
            predictions = self.pattern_engine.predict_dependencies(task, candidate_tasks)
            
            # Filter predictions by minimum confidence threshold
            min_confidence = 0.4
            filtered_predictions = [p for p in predictions if p.confidence >= min_confidence]
            
            self.logger.info(f"Generated {len(filtered_predictions)} predictions for task {getattr(task, 'id', 'unknown')}")
            return filtered_predictions
            
        except Exception as e:
            self.logger.error(f"Error predicting dependencies: {e}")
            return []
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        try:
            info = {
                'trained': self.pattern_engine.trained,
                'available_versions': self.persistence.get_available_versions(),
                'current_stats': self.pattern_engine.get_engine_stats() if self.pattern_engine.trained else None,
                'model_directory': str(self.persistence.model_dir)
            }
            
            # Add metadata for latest version if available
            versions = self.persistence.get_available_versions()
            if versions:
                latest_version = versions[0]
                metadata_file = self.persistence.model_dir / f"metadata_{latest_version}.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        info['latest_version_metadata'] = json.load(f)
            
            return info
            
        except Exception as e:
            self.logger.error(f"Error getting model info: {e}")
            return {'error': str(e)}
    
    def retrain_model(self) -> Dict[str, Any]:
        """Retrain the model with latest data"""
        self.logger.info("Retraining model with latest data")
        return self.train_model(save_model=True)
    
    def update_pattern_feedback(self, pattern_id: str, accepted: bool) -> bool:
        """
        Update pattern with user feedback
        
        Args:
            pattern_id: ID of the pattern to update
            accepted: Whether the user accepted the suggestion based on this pattern
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            if pattern_id in self.pattern_engine.patterns:
                pattern = self.pattern_engine.patterns[pattern_id]
                
                # Update success rate based on feedback
                if accepted:
                    pattern.success_rate = (pattern.success_rate * pattern.support_count + 1.0) / (pattern.support_count + 1)
                else:
                    pattern.success_rate = (pattern.success_rate * pattern.support_count) / (pattern.support_count + 1)
                
                pattern.support_count += 1
                pattern.last_updated = datetime.now(timezone.utc)
                
                self.logger.info(f"Updated pattern {pattern_id} with feedback: {'accepted' if accepted else 'rejected'}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating pattern feedback: {e}")
            return False