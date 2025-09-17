"""
Content Analyzer - Domain service for analyzing task content to identify dependencies

This service provides domain-level logic for parsing and analyzing task content
to automatically detect potential dependency relationships.
"""

import logging
import re
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """Types of content analysis"""
    KEYWORD = "keyword"
    FILE_REFERENCE = "file_reference"
    ENTITY_EXTRACTION = "entity_extraction"
    TEMPORAL_PATTERN = "temporal_pattern"
    SEMANTIC_SIMILARITY = "semantic_similarity"


@dataclass
class ContentFeature:
    """Represents a feature extracted from task content"""
    feature_type: AnalysisType
    value: str
    confidence: float
    position: int = 0
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityMatch:
    """Represents a matched entity between tasks"""
    entity: str
    source_task_id: str
    target_task_id: str
    match_type: str
    confidence: float
    evidence: List[str] = field(default_factory=list)


class ContentAnalyzer:
    """
    Domain service for intelligent content analysis of tasks
    
    This service provides sophisticated text analysis capabilities including:
    - Keyword extraction and dependency inference
    - File reference detection and cross-referencing
    - Entity extraction (database tables, API endpoints, etc.)
    - Temporal pattern recognition
    - Semantic similarity analysis
    """
    
    # Enhanced dependency keywords with context patterns
    DEPENDENCY_PATTERNS = {
        # Direct dependency indicators - more flexible patterns without strict lookaheads
        r'\b(?:requires?|needs?|depends?\s+on)\s+(?:the\s+)?([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b': 0.9,
        r'\b(?:after|following)\s+(?:the\s+)?([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b': 0.8,
        r'\b(?:before|preceding)\s+(?:the\s+)?([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b': 0.8,
        r'\b(?:blocks?|blocked\s+by)\s+(?:the\s+)?([A-Za-z][a-zA-Z]*(?:\s+[a-zA-Z]+)*)\b': 1.0,
        r'\b(?:prerequisite|prerequist)\s+(?:the\s+)?([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b': 0.9,
        
        # Implementation relationships
        r'\b(?:implements?|implementation\s+of)\s+(["\']?[\w\s\-]+["\']?)': 0.7,
        r'\b(?:extends?|extension\s+of)\s+(["\']?[\w\s\-]+["\']?)': 0.7,
        r'\b(?:inherits?\s+from|based\s+on)\s+(["\']?[\w\s\-]+["\']?)': 0.6,
        r'\b(?:uses?|utilizes?)\s+(["\']?[\w\s\-]+["\']?)': 0.5,
        
        # Sequential relationships
        r'\b(?:first|initially|start\s+with)\s+(["\']?[\w\s\-]+["\']?)': 0.7,
        r'\b(?:then|next|followed\s+by)\s+(["\']?[\w\s\-]+["\']?)': 0.8,
        r'\b(?:finally|last|end\s+with)\s+(["\']?[\w\s\-]+["\']?)': 0.6,
    }
    
    # File patterns for different project types
    FILE_PATTERNS = {
        'source_code': r'(?:src/|source/)?[\w\-/]+\.(?:py|js|ts|tsx|jsx|java|cpp|c|h|php|rb|go|rs|swift|kt)',
        'config_files': r'(?:config/|conf/)?[\w\-/]+\.(?:json|yaml|yml|toml|ini|cfg|properties)',
        'documentation': r'(?:docs?/|documentation/)?[\w\-/]+\.(?:md|rst|txt|adoc)',
        'database': r'(?:migrations?/|schema/|db/)?[\w\-/]+\.(?:sql|migration|schema)',
        'tests': r'(?:tests?/|spec/|__tests__/)?[\w\-/]+\.(?:test|spec)\.(?:py|js|ts|java|cpp)',
        'static_assets': r'(?:static/|assets/|public/)?[\w\-/]+\.(?:css|scss|less|png|jpg|jpeg|svg|ico)',
        'templates': r'(?:templates?/|views?/)?[\w\-/]+\.(?:html|jinja|tpl|blade|erb)',
    }
    
    # Technical entities that often indicate dependencies
    TECHNICAL_ENTITIES = {
        'database_objects': r'\b(?:table|view|procedure|function|trigger|index)\s+([a-z_][a-z0-9_]*)\b',
        'api_endpoints': r'\b(?:GET|POST|PUT|DELETE|PATCH)\s+([/\w\-{}]+)',
        'api_routes': r'(?:route|endpoint|path)[\s:]+([/\w\-{}]+)',
        'class_references': r'\bclass\s+([A-Z][a-zA-Z0-9_]*)\b',
        'function_references': r'\bfunction\s+([a-z_][a-zA-Z0-9_]*)\b',
        'method_references': r'\.([a-z_][a-zA-Z0-9_]*)\s*\(',
        'module_imports': r'\b(?:import|from)\s+([\w\.]+)',
        'component_names': r'\b([A-Z][a-zA-Z0-9]*Component)\b',
        'service_names': r'\b([A-Z][a-zA-Z0-9]*Service)\b',
        'model_names': r'\b([A-Z][a-zA-Z0-9]*Model)\b',
        # Add pattern for capitalized multi-word entities like "User Model" - requires ALL words to be capitalized
        'entity_names': r'\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)+)\b',
    }
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def extract_features(self, task_content: str) -> List[ContentFeature]:
        """
        Extract all features from task content
        
        Args:
            task_content: Combined text content from task
            
        Returns:
            List of extracted content features
        """
        features = []
        
        # Extract keyword features
        features.extend(self._extract_keyword_features(task_content))
        
        # Extract file reference features
        features.extend(self._extract_file_features(task_content))
        
        # Extract technical entity features
        features.extend(self._extract_entity_features(task_content))
        
        # Extract temporal pattern features
        features.extend(self._extract_temporal_features(task_content))
        
        return features
    
    def find_content_matches(self, source_features: List[ContentFeature], target_content: str) -> List[EntityMatch]:
        """
        Find matches between source features and target content
        
        Args:
            source_features: Features extracted from source task
            target_content: Content of target task to match against
            
        Returns:
            List of entity matches with confidence scores
        """
        matches = []
        target_features = self.extract_features(target_content)
        
        for source_feature in source_features:
            for target_feature in target_features:
                match = self._calculate_feature_match(source_feature, target_feature)
                if match and match.confidence > 0.3:  # Minimum threshold
                    matches.append(match)
        
        return matches
    
    def _extract_keyword_features(self, content: str) -> List[ContentFeature]:
        """Extract dependency keywords from content"""
        features = []
        content_lower = content.lower()
        
        for pattern, confidence in self.DEPENDENCY_PATTERNS.items():
            matches = re.finditer(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                # Extract the referenced entity
                entity = match.group(1) if match.groups() else match.group(0)
                entity = entity.strip('\'"')  # Remove quotes
                
                feature = ContentFeature(
                    feature_type=AnalysisType.KEYWORD,
                    value=entity,
                    confidence=confidence,
                    position=match.start(),
                    context=content[max(0, match.start()-50):match.end()+50],
                    metadata={
                        'pattern': pattern,
                        'full_match': match.group(0)
                    }
                )
                features.append(feature)
        
        return features
    
    def _extract_file_features(self, content: str) -> List[ContentFeature]:
        """Extract file references from content"""
        features = []
        
        for file_type, pattern in self.FILE_PATTERNS.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                file_path = match.group(0)
                
                # Calculate confidence based on file type and context
                confidence = 0.6
                if file_type in ['source_code', 'config_files', 'database']:
                    confidence = 0.8
                elif file_type == 'tests':
                    confidence = 0.7
                
                feature = ContentFeature(
                    feature_type=AnalysisType.FILE_REFERENCE,
                    value=file_path,
                    confidence=confidence,
                    position=match.start(),
                    context=content[max(0, match.start()-30):match.end()+30],
                    metadata={
                        'file_type': file_type,
                        'extension': file_path.split('.')[-1] if '.' in file_path else ''
                    }
                )
                features.append(feature)
        
        return features
    
    def _extract_entity_features(self, content: str) -> List[ContentFeature]:
        """Extract technical entities from content"""
        features = []

        for entity_type, pattern in self.TECHNICAL_ENTITIES.items():
            # Use case-sensitive matching for entity_names to ensure proper capitalization
            flags = 0 if entity_type == 'entity_names' else re.IGNORECASE
            matches = re.finditer(pattern, content, flags)
            for match in matches:
                entity_name = match.group(1) if match.groups() else match.group(0)
                
                # Confidence based on entity type
                confidence_map = {
                    'database_objects': 0.9,
                    'api_endpoints': 0.8,
                    'class_references': 0.7,
                    'function_references': 0.6,
                    'module_imports': 0.8,
                    'component_names': 0.7,
                    'service_names': 0.7,
                    'model_names': 0.7,
                    'entity_names': 0.6,
                }
                confidence = confidence_map.get(entity_type, 0.5)
                
                feature = ContentFeature(
                    feature_type=AnalysisType.ENTITY_EXTRACTION,
                    value=entity_name,
                    confidence=confidence,
                    position=match.start(),
                    context=content[max(0, match.start()-40):match.end()+40],
                    metadata={
                        'entity_type': entity_type,
                        'full_match': match.group(0)
                    }
                )
                features.append(feature)
        
        return features
    
    def _extract_temporal_features(self, content: str) -> List[ContentFeature]:
        """Extract temporal/sequential patterns from content"""
        features = []
        
        temporal_patterns = [
            (r'\bstep\s+(\d+)', 0.8),
            (r'\bphase\s+(\d+)', 0.7),
            (r'\bstage\s+(\d+)', 0.7),
            (r'\border\s*:\s*(\d+)', 0.6),
            (r'\bsequence\s*:\s*(\d+)', 0.6),
            (r'\b(first|second|third|fourth|fifth|last)\s+step', 0.7),
        ]
        
        for pattern, confidence in temporal_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                sequence_indicator = match.group(1) if match.groups() else match.group(0)
                
                feature = ContentFeature(
                    feature_type=AnalysisType.TEMPORAL_PATTERN,
                    value=sequence_indicator,
                    confidence=confidence,
                    position=match.start(),
                    context=content[max(0, match.start()-30):match.end()+30],
                    metadata={
                        'pattern': pattern,
                        'sequence_type': 'ordered' if sequence_indicator.isdigit() else 'sequential'
                    }
                )
                features.append(feature)
        
        return features
    
    def _calculate_feature_match(self, source_feature: ContentFeature, target_feature: ContentFeature) -> Optional[EntityMatch]:
        """Calculate match between two content features"""
        
        # Features must be compatible types
        compatible_types = {
            AnalysisType.KEYWORD: [AnalysisType.KEYWORD, AnalysisType.ENTITY_EXTRACTION],
            AnalysisType.FILE_REFERENCE: [AnalysisType.FILE_REFERENCE],
            AnalysisType.ENTITY_EXTRACTION: [AnalysisType.ENTITY_EXTRACTION, AnalysisType.KEYWORD],
            AnalysisType.TEMPORAL_PATTERN: [AnalysisType.TEMPORAL_PATTERN],
        }
        
        if target_feature.feature_type not in compatible_types.get(source_feature.feature_type, []):
            return None
        
        # Calculate string similarity
        similarity = self._calculate_string_similarity(source_feature.value, target_feature.value)
        
        # Dynamic threshold based on feature type and confidence
        if source_feature.feature_type == AnalysisType.KEYWORD or target_feature.feature_type == AnalysisType.KEYWORD:
            min_threshold = 0.3  # More permissive for keyword matches
        elif source_feature.confidence > 0.7 or target_feature.confidence > 0.7:
            min_threshold = 0.3  # More permissive for high confidence features
        else:
            min_threshold = 0.5  # Default threshold

        if similarity < min_threshold:
            return None
        
        # Calculate confidence based on feature types and similarity
        base_confidence = (source_feature.confidence + target_feature.confidence) / 2
        confidence = base_confidence * similarity
        
        # Boost confidence for exact matches
        if similarity >= 0.95:
            confidence *= 1.2
        
        # Cap confidence at 0.95
        confidence = min(confidence, 0.95)
        
        return EntityMatch(
            entity=source_feature.value,
            source_task_id="",  # Will be set by caller
            target_task_id="",  # Will be set by caller
            match_type=f"{source_feature.feature_type.value}_{target_feature.feature_type.value}",
            confidence=confidence,
            evidence=[
                f"Source: {source_feature.context[:100]}",
                f"Target: {target_feature.context[:100]}",
                f"Similarity: {similarity:.2f}"
            ]
        )
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using multiple methods"""
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        if str1 == str2:
            return 1.0
        
        # Exact substring match
        if str1 in str2 or str2 in str1:
            shorter = min(len(str1), len(str2))
            longer = max(len(str1), len(str2))
            return shorter / longer
        
        # Token-based similarity (split by spaces, underscores, hyphens)
        tokens1 = set(re.split(r'[\s_\-]+', str1))
        tokens2 = set(re.split(r'[\s_\-]+', str2))
        
        if tokens1 and tokens2:
            intersection = tokens1.intersection(tokens2)
            union = tokens1.union(tokens2)
            token_similarity = len(intersection) / len(union)
            
            # If we have good token overlap, return higher score
            if token_similarity > 0.3:
                return token_similarity
        
        # Levenshtein-like similarity for short strings
        if len(str1) <= 20 and len(str2) <= 20:
            return self._simple_edit_distance_similarity(str1, str2)
        
        return 0.0
    
    def _simple_edit_distance_similarity(self, str1: str, str2: str) -> float:
        """Simple edit distance similarity calculation"""
        if not str1 or not str2:
            return 0.0
        
        # Simple character-based similarity
        common_chars = sum(1 for c in str1 if c in str2)
        max_len = max(len(str1), len(str2))
        
        return common_chars / max_len
    
    def analyze_task_relationships(self, task_contents: Dict[str, str]) -> Dict[str, List[EntityMatch]]:
        """
        Analyze relationships between multiple tasks
        
        Args:
            task_contents: Dictionary mapping task_id to task content
            
        Returns:
            Dictionary mapping source task_id to list of matches with other tasks
        """
        relationships = {}
        task_features = {}
        
        # Extract features for all tasks
        for task_id, content in task_contents.items():
            task_features[task_id] = self.extract_features(content)
        
        # Find matches between all task pairs
        task_ids = list(task_contents.keys())
        for i, source_task_id in enumerate(task_ids):
            relationships[source_task_id] = []
            
            for j, target_task_id in enumerate(task_ids):
                if i == j:  # Skip self
                    continue
                
                source_features = task_features[source_task_id]
                target_content = task_contents[target_task_id]
                
                matches = self.find_content_matches(source_features, target_content)
                for match in matches:
                    match.source_task_id = source_task_id
                    match.target_task_id = target_task_id
                    relationships[source_task_id].append(match)
        
        return relationships
    
    def get_analysis_summary(self, features: List[ContentFeature]) -> Dict[str, Any]:
        """Generate summary statistics for content analysis"""
        summary = {
            'total_features': len(features),
            'feature_types': {},
            'high_confidence_features': 0,
            'avg_confidence': 0.0,
            'extracted_entities': [],
            'file_references': [],
        }
        
        if not features:
            return summary
        
        # Count by type
        for feature in features:
            feature_type = feature.feature_type.value
            summary['feature_types'][feature_type] = summary['feature_types'].get(feature_type, 0) + 1
            
            if feature.confidence > 0.7:
                summary['high_confidence_features'] += 1
            
            if feature.feature_type == AnalysisType.ENTITY_EXTRACTION:
                summary['extracted_entities'].append(feature.value)
            elif feature.feature_type == AnalysisType.FILE_REFERENCE:
                summary['file_references'].append(feature.value)
        
        summary['avg_confidence'] = sum(f.confidence for f in features) / len(features)
        
        return summary