"""
Pattern Recognition Engine - ML-based dependency pattern learning and prediction

This engine learns from historical task dependencies to predict likely dependencies
for new tasks using machine learning techniques.
"""

import logging
import json

# Optional numpy import with fallback
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    # Mock numpy functions when not available
    class MockNumpy:
        @staticmethod
        def mean(values):
            return sum(values) / len(values) if values else 0.0
    
    np = MockNumpy()
    NUMPY_AVAILABLE = False
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict, Counter
from enum import Enum

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of dependency patterns"""
    SEQUENTIAL = "sequential"          # A -> B -> C patterns
    PARALLEL = "parallel"              # A -> (B, C) patterns  
    CONVERGING = "converging"          # (A, B) -> C patterns
    BRANCHING = "branching"            # A -> (B, C, D) patterns
    CYCLICAL = "cyclical"              # Recurring patterns across projects
    AGENT_BASED = "agent_based"        # Agent assignment patterns
    TEMPORAL = "temporal"              # Time-based patterns


@dataclass
class TaskVector:
    """Vector representation of a task for ML processing"""
    task_id: str
    title_tokens: List[str]
    description_tokens: List[str]
    agents: List[str]
    priority: str
    estimated_effort: str
    file_references: List[str]
    technical_entities: List[str]
    creation_time: datetime
    completion_time: Optional[datetime] = None


@dataclass
class DependencyPattern:
    """Represents a learned dependency pattern"""
    pattern_id: str
    pattern_type: PatternType
    source_features: Dict[str, Any]
    target_features: Dict[str, Any]
    confidence: float
    support_count: int  # How many times we've seen this pattern
    success_rate: float  # How often this pattern led to successful dependencies
    created_at: datetime
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternPrediction:
    """A predicted dependency based on learned patterns"""
    source_task_id: str
    target_task_id: str
    pattern_ids: List[str]
    confidence: float
    reasoning: str
    features_matched: List[str]
    pattern_evidence: Dict[str, Any] = field(default_factory=dict)


class FeatureExtractor:
    """Extracts features from tasks for ML processing"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # Common stop words to filter out
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'from', 'into', 'through', 'during', 'before', 
            'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under'
        }
    
    def extract_task_vector(self, task) -> TaskVector:
        """Extract feature vector from a task"""
        try:
            # Tokenize text content
            title_tokens = self._tokenize_text(getattr(task, 'title', '') or "")
            # Safely get details attribute - it may not exist in all task objects
            details = getattr(task, 'details', '') or ""
            description_tokens = self._tokenize_text(
                (getattr(task, 'description', '') or "") + " " + details
            )

            # Extract file references
            file_references = self._extract_file_references(
                (getattr(task, 'description', '') or "") + " " + details
            )

            # Extract technical entities
            technical_entities = self._extract_technical_entities(
                (getattr(task, 'description', '') or "") + " " + details
            )
            
            return TaskVector(
                task_id=str(task.id),
                title_tokens=title_tokens,
                description_tokens=description_tokens,
                agents=getattr(task, 'assignees', []).copy() if getattr(task, 'assignees', []) else [],
                priority=task.priority.value if hasattr(task.priority, 'value') else str(getattr(task, 'priority', 'medium')),
                estimated_effort=getattr(task, 'estimated_effort', None) or "unknown",
                file_references=file_references,
                technical_entities=technical_entities,
                creation_time=getattr(task, 'created_at', datetime.now(timezone.utc)),
                completion_time=getattr(task, 'completed_at', None)
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting features from task {getattr(task, 'id', 'unknown')}: {e}")
            # Return minimal vector
            return TaskVector(
                task_id=str(getattr(task, 'id', 'unknown')),
                title_tokens=[],
                description_tokens=[],
                agents=[],
                priority="medium",
                estimated_effort="unknown",
                file_references=[],
                technical_entities=[],
                creation_time=datetime.now(timezone.utc)
            )
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text into meaningful words"""
        import re
        
        if not text:
            return []
        
        # Convert to lowercase and extract alphanumeric tokens
        tokens = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_]*\b', text.lower())
        
        # Filter out stop words and very short tokens
        filtered_tokens = [
            token for token in tokens 
            if token not in self.stop_words and len(token) > 2
        ]
        
        return filtered_tokens[:50]  # Limit to prevent huge vectors
    
    def _extract_file_references(self, text: str) -> List[str]:
        """Extract file paths from text"""
        import re
        
        file_patterns = [
            r'[\w\-/]+\.(?:py|js|ts|tsx|jsx|java|cpp|c|h|php|rb|go|rs|swift|kt|sql|json|yaml|yml|md)',
            r'(?:src|test|config|docs?)/[\w\-/]+',
        ]
        
        file_refs = []
        for pattern in file_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            file_refs.extend(matches)
        
        return list(set(file_refs))[:20]  # Limit and deduplicate
    
    def _extract_technical_entities(self, text: str) -> List[str]:
        """Extract technical entities from text"""
        import re
        
        entity_patterns = [
            r'\b[A-Z][a-zA-Z0-9]*(?:Service|Controller|Model|Component|Manager|Handler|Repository)\b',
            r'\b(?:GET|POST|PUT|DELETE|PATCH)\s+[/\w\-{}]+',
            r'\btable\s+([a-z_][a-z0-9_]*)\b',
            r'\bclass\s+([A-Z][a-zA-Z0-9_]*)\b',
        ]
        
        entities = []
        for pattern in entity_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if isinstance(matches[0] if matches else None, tuple):
                entities.extend([m[0] for m in matches])
            else:
                entities.extend(matches)
        
        return list(set(entities))[:15]  # Limit and deduplicate


class PatternLearner:
    """Learns patterns from historical dependency data"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.feature_extractor = FeatureExtractor()
        self.patterns: Dict[str, DependencyPattern] = {}
        self.pattern_counter = 0
    
    def learn_from_project_history(self, project_data: List[Dict[str, Any]]) -> List[DependencyPattern]:
        """
        Learn patterns from historical project data
        
        Args:
            project_data: List of project dictionaries with tasks and dependencies
            
        Returns:
            List of learned patterns
        """
        new_patterns = []
        
        for project in project_data:
            try:
                project_patterns = self._analyze_project_patterns(project)
                new_patterns.extend(project_patterns)
            except Exception as e:
                self.logger.error(f"Error analyzing project {project.get('id', 'unknown')}: {e}")
        
        # Store patterns
        for pattern in new_patterns:
            self.patterns[pattern.pattern_id] = pattern
        
        self.logger.info(f"Learned {len(new_patterns)} new patterns from {len(project_data)} projects")
        return new_patterns
    
    def _analyze_project_patterns(self, project: Dict[str, Any]) -> List[DependencyPattern]:
        """Analyze patterns within a single project"""
        patterns = []
        tasks = project.get('tasks', [])
        
        if len(tasks) < 2:
            return patterns
        
        # Extract task vectors
        task_vectors = {}
        for task_data in tasks:
            # Convert dict to object-like structure for feature extraction
            class TaskObj:
                def __init__(self, data):
                    for k, v in data.items():
                        setattr(self, k, v)
            
            task_obj = TaskObj(task_data)
            vector = self.feature_extractor.extract_task_vector(task_obj)
            task_vectors[vector.task_id] = vector
        
        # Analyze dependency patterns
        for task_data in tasks:
            task_id = str(task_data.get('id', ''))
            dependencies = task_data.get('dependencies', [])
            
            if not dependencies:
                continue
            
            source_vector = task_vectors.get(task_id)
            if not source_vector:
                continue
            
            for dep_id in dependencies:
                target_vector = task_vectors.get(str(dep_id))
                if not target_vector:
                    continue
                
                # Identify pattern type
                pattern_type = self._identify_pattern_type(
                    source_vector, target_vector, task_vectors, dependencies
                )
                
                # Extract features that characterize this dependency
                pattern = self._extract_dependency_pattern(
                    source_vector, target_vector, pattern_type, project
                )
                
                if pattern:
                    patterns.append(pattern)
        
        return patterns
    
    def _identify_pattern_type(
        self,
        source: TaskVector,
        target: TaskVector,
        all_vectors: Dict[str, TaskVector],
        all_deps: List[str]
    ) -> PatternType:
        """Identify the type of pattern this dependency represents"""

        # Check branching patterns first (multiple dependencies)
        if len(all_deps) > 2:
            return PatternType.BRANCHING

        # Check agent-based patterns for partial overlap (different teams with overlap)
        if source.agents and target.agents:
            source_agents_set = set(source.agents)
            target_agents_set = set(target.agents)
            if source_agents_set != target_agents_set and source_agents_set.intersection(target_agents_set):
                return PatternType.AGENT_BASED

        # Check temporal patterns (for same team or when agents don't have partial overlap)
        if source.creation_time and target.creation_time:
            if source.creation_time > target.creation_time:
                return PatternType.SEQUENTIAL

        # Check agent-based patterns for exact same agents (fallback)
        if source.agents and target.agents:
            if set(source.agents) == set(target.agents):
                return PatternType.AGENT_BASED

        # Default to sequential
        return PatternType.SEQUENTIAL
    
    def _extract_dependency_pattern(
        self, 
        source: TaskVector, 
        target: TaskVector, 
        pattern_type: PatternType,
        project_context: Dict[str, Any]
    ) -> Optional[DependencyPattern]:
        """Extract a dependency pattern from two related tasks"""
        
        try:
            pattern_id = f"pattern_{self.pattern_counter}"
            self.pattern_counter += 1
            
            # Extract features that make this a meaningful pattern
            source_features = self._extract_pattern_features(source)
            target_features = self._extract_pattern_features(target)
            
            # Calculate initial confidence based on feature richness
            confidence = self._calculate_pattern_confidence(source_features, target_features)

            if confidence < 0.3:  # Skip very weak patterns
                return None
            
            pattern = DependencyPattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                source_features=source_features,
                target_features=target_features,
                confidence=confidence,
                support_count=1,
                success_rate=1.0,  # Assume historical dependencies were successful
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                metadata={
                    'project_id': project_context.get('id', ''),
                    'project_domain': project_context.get('domain', 'unknown'),
                    'source_task_id': source.task_id,
                    'target_task_id': target.task_id
                }
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"Error extracting pattern: {e}")
            return None
    
    def _extract_pattern_features(self, vector: TaskVector) -> Dict[str, Any]:
        """Extract features that characterize a task for pattern matching"""
        
        # Get most common tokens (keywords that define the task)
        title_keywords = Counter(vector.title_tokens).most_common(5)
        desc_keywords = Counter(vector.description_tokens).most_common(10)
        
        features = {
            'title_keywords': [word for word, count in title_keywords],
            'description_keywords': [word for word, count in desc_keywords],
            'agents': vector.agents,
            'priority': vector.priority,
            'estimated_effort': vector.estimated_effort,
            'has_files': len(vector.file_references) > 0,
            'file_types': list(set([
                ref.split('.')[-1] for ref in vector.file_references 
                if '.' in ref
            ])),
            'has_entities': len(vector.technical_entities) > 0,
            'entity_types': self._categorize_entities(vector.technical_entities)
        }
        
        return features
    
    def _categorize_entities(self, entities: List[str]) -> List[str]:
        """Categorize technical entities by type"""
        categories = []
        
        for entity in entities:
            if entity.endswith(('Service', 'service')):
                categories.append('service')
            elif entity.endswith(('Controller', 'controller')):
                categories.append('controller')
            elif entity.endswith(('Model', 'model')):
                categories.append('model')
            elif entity.endswith(('Component', 'component')):
                categories.append('component')
            elif entity.startswith(('GET', 'POST', 'PUT', 'DELETE')):
                categories.append('api_endpoint')
            elif 'table' in entity.lower():
                categories.append('database')
            else:
                categories.append('other')
        
        return list(set(categories))
    
    def _calculate_pattern_confidence(
        self, 
        source_features: Dict[str, Any], 
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate confidence that this represents a meaningful pattern"""
        
        confidence_factors = []
        
        # Keyword similarity
        source_keywords = set(source_features['title_keywords'] + source_features['description_keywords'])
        target_keywords = set(target_features['title_keywords'] + target_features['description_keywords'])
        
        if source_keywords and target_keywords:
            keyword_overlap = len(source_keywords.intersection(target_keywords))
            keyword_union = len(source_keywords.union(target_keywords))
            keyword_similarity = keyword_overlap / keyword_union if keyword_union > 0 else 0
            confidence_factors.append(keyword_similarity)
        
        # Agent similarity
        source_agents = set(source_features['agents'])
        target_agents = set(target_features['agents'])
        
        if source_agents and target_agents:
            agent_overlap = len(source_agents.intersection(target_agents))
            agent_similarity = agent_overlap / len(source_agents.union(target_agents))
            confidence_factors.append(agent_similarity * 0.8)  # Weight agent similarity
        
        # File type similarity
        source_file_types = set(source_features['file_types'])
        target_file_types = set(target_features['file_types'])
        
        if source_file_types and target_file_types:
            file_overlap = len(source_file_types.intersection(target_file_types))
            file_similarity = file_overlap / len(source_file_types.union(target_file_types))
            confidence_factors.append(file_similarity * 0.6)
        
        # Entity type similarity
        source_entities = set(source_features['entity_types'])
        target_entities = set(target_features['entity_types'])
        
        if source_entities and target_entities:
            entity_overlap = len(source_entities.intersection(target_entities))
            entity_similarity = entity_overlap / len(source_entities.union(target_entities))
            confidence_factors.append(entity_similarity * 0.7)
        
        # Return average confidence if we have factors, otherwise low confidence
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.2


class PatternRecognitionEngine:
    """
    Main engine for pattern-based dependency prediction
    
    Uses machine learning techniques to learn from historical dependency patterns
    and predict likely dependencies for new tasks.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.feature_extractor = FeatureExtractor()
        self.pattern_learner = PatternLearner()
        self.patterns: Dict[str, DependencyPattern] = {}
        self.trained = False
    
    def train_from_historical_data(self, project_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train the engine from historical project data
        
        Args:
            project_history: List of completed projects with task and dependency data
            
        Returns:
            Training summary with statistics
        """
        self.logger.info(f"Starting training with {len(project_history)} projects")
        
        # Learn patterns
        learned_patterns = self.pattern_learner.learn_from_project_history(project_history)
        
        # Store patterns
        for pattern in learned_patterns:
            self.patterns[pattern.pattern_id] = pattern
        
        self.trained = True
        
        # Generate summary
        pattern_types = Counter([p.pattern_type.value for p in learned_patterns])
        avg_confidence = np.mean([p.confidence for p in learned_patterns]) if learned_patterns else 0.0
        
        summary = {
            'total_projects': len(project_history),
            'patterns_learned': len(learned_patterns),
            'pattern_types': dict(pattern_types),
            'average_confidence': float(avg_confidence),
            'training_completed_at': datetime.now(timezone.utc).isoformat()
        }
        
        self.logger.info(f"Training completed: {summary}")
        return summary
    
    def predict_dependencies(self, task, available_tasks: List) -> List[PatternPrediction]:
        """
        Predict dependencies for a task based on learned patterns
        
        Args:
            task: Task to predict dependencies for
            available_tasks: List of tasks that could be dependencies
            
        Returns:
            List of dependency predictions with confidence scores
        """
        if not self.trained or not self.patterns:
            self.logger.warning("Engine not trained or no patterns available")
            return []
        
        predictions = []
        
        try:
            # Extract features from the target task
            source_vector = self.feature_extractor.extract_task_vector(task)
            source_features = self.pattern_learner._extract_pattern_features(source_vector)
            
            # Compare against available tasks
            for candidate_task in available_tasks:
                if str(candidate_task.id) == str(task.id):
                    continue  # Skip self
                
                candidate_vector = self.feature_extractor.extract_task_vector(candidate_task)
                candidate_features = self.pattern_learner._extract_pattern_features(candidate_vector)
                
                # Find matching patterns
                matching_patterns = self._find_matching_patterns(source_features, candidate_features)
                
                if matching_patterns:
                    prediction = self._create_prediction(
                        source_vector.task_id,
                        candidate_vector.task_id,
                        matching_patterns
                    )
                    predictions.append(prediction)
            
            # Sort by confidence and return top predictions
            predictions.sort(key=lambda p: p.confidence, reverse=True)
            return predictions[:5]  # Limit to top 5 predictions
            
        except Exception as e:
            self.logger.error(f"Error predicting dependencies for task {getattr(task, 'id', 'unknown')}: {e}")
            return []
    
    def _find_matching_patterns(
        self, 
        source_features: Dict[str, Any], 
        target_features: Dict[str, Any]
    ) -> List[DependencyPattern]:
        """Find patterns that match the given feature combination"""
        
        matching_patterns = []
        
        for pattern in self.patterns.values():
            match_score = self._calculate_pattern_match_score(
                source_features, target_features, pattern
            )
            
            if match_score > 0.5:  # Minimum match threshold
                # Update pattern with current match score
                pattern.metadata['current_match_score'] = match_score
                matching_patterns.append(pattern)
        
        # Sort by match score
        matching_patterns.sort(
            key=lambda p: p.metadata.get('current_match_score', 0), 
            reverse=True
        )
        
        return matching_patterns
    
    def _calculate_pattern_match_score(
        self, 
        source_features: Dict[str, Any], 
        target_features: Dict[str, Any],
        pattern: DependencyPattern
    ) -> float:
        """Calculate how well the current feature pair matches a learned pattern"""
        
        match_scores = []
        
        # Match source features
        source_match = self._match_features(source_features, pattern.source_features)
        match_scores.append(source_match)
        
        # Match target features
        target_match = self._match_features(target_features, pattern.target_features)
        match_scores.append(target_match)
        
        # Weight by pattern success rate and support count
        base_score = np.mean(match_scores) if match_scores else 0.0
        
        # Boost score for patterns with high success rate and support
        success_boost = pattern.success_rate * 0.2
        support_boost = min(0.1, pattern.support_count / 10.0)  # Cap support boost
        
        final_score = base_score + success_boost + support_boost
        
        return min(final_score, 1.0)  # Cap at 1.0
    
    def _match_features(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """Calculate feature similarity between two feature sets"""
        
        similarity_scores = []
        
        # Compare keyword lists
        for key in ['title_keywords', 'description_keywords']:
            if key in features1 and key in features2:
                set1 = set(features1[key])
                set2 = set(features2[key])
                if set1 or set2:
                    overlap = len(set1.intersection(set2))
                    union = len(set1.union(set2))
                    similarity = overlap / union if union > 0 else 0
                    similarity_scores.append(similarity)
        
        # Compare agent lists
        if 'agents' in features1 and 'agents' in features2:
            agents1 = set(features1['agents'])
            agents2 = set(features2['agents'])
            if agents1 or agents2:
                overlap = len(agents1.intersection(agents2))
                union = len(agents1.union(agents2))
                similarity = overlap / union if union > 0 else 0
                similarity_scores.append(similarity * 1.5)  # Weight agent matches higher
        
        # Compare categorical features
        for key in ['priority', 'estimated_effort']:
            if key in features1 and key in features2:
                if features1[key] == features2[key]:
                    similarity_scores.append(1.0)
                else:
                    similarity_scores.append(0.0)
        
        # Compare file types and entity types
        for key in ['file_types', 'entity_types']:
            if key in features1 and key in features2:
                set1 = set(features1[key])
                set2 = set(features2[key])
                if set1 or set2:
                    overlap = len(set1.intersection(set2))
                    union = len(set1.union(set2))
                    similarity = overlap / union if union > 0 else 0
                    similarity_scores.append(similarity)
        
        return np.mean(similarity_scores) if similarity_scores else 0.0
    
    def _create_prediction(
        self, 
        source_task_id: str, 
        target_task_id: str, 
        matching_patterns: List[DependencyPattern]
    ) -> PatternPrediction:
        """Create a prediction from matching patterns"""
        
        # Calculate overall confidence as weighted average
        total_weight = sum(p.confidence * p.support_count for p in matching_patterns)
        total_support = sum(p.support_count for p in matching_patterns)
        
        confidence = total_weight / total_support if total_support > 0 else 0.0
        
        # Generate reasoning
        pattern_types = [p.pattern_type.value for p in matching_patterns]
        most_common_type = Counter(pattern_types).most_common(1)[0][0] if pattern_types else 'unknown'
        
        reasoning = f"Predicted based on {len(matching_patterns)} similar {most_common_type} pattern(s) " \
                   f"with average support of {total_support / len(matching_patterns):.1f}"
        
        # Extract matched features for explanation
        features_matched = []
        for pattern in matching_patterns[:3]:  # Top 3 patterns
            if pattern.metadata.get('current_match_score', 0) > 0.7:
                features_matched.append(f"{pattern.pattern_type.value} (score: {pattern.metadata['current_match_score']:.2f})")
        
        return PatternPrediction(
            source_task_id=source_task_id,
            target_task_id=target_task_id,
            pattern_ids=[p.pattern_id for p in matching_patterns],
            confidence=confidence,
            reasoning=reasoning,
            features_matched=features_matched,
            pattern_evidence={
                'matching_patterns': len(matching_patterns),
                'avg_support': total_support / len(matching_patterns) if matching_patterns else 0,
                'pattern_types': pattern_types
            }
        )
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get statistics about the pattern recognition engine"""
        if not self.patterns:
            return {'status': 'not_trained', 'patterns': 0}
        
        pattern_types = Counter([p.pattern_type.value for p in self.patterns.values()])
        avg_confidence = np.mean([p.confidence for p in self.patterns.values()])
        avg_support = np.mean([p.support_count for p in self.patterns.values()])
        
        return {
            'status': 'trained' if self.trained else 'not_trained',
            'total_patterns': len(self.patterns),
            'pattern_types': dict(pattern_types),
            'average_confidence': float(avg_confidence),
            'average_support': float(avg_support),
            'last_updated': max([p.last_updated for p in self.patterns.values()]).isoformat() if self.patterns else None
        }