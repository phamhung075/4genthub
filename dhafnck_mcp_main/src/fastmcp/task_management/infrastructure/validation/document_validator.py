"""Document Validator

Infrastructure component for validating documents and their metadata.
"""

import logging
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from ...domain.enums.compliance_enums import DocumentType
from ...domain.value_objects.compliance_objects import DocumentInfo

logger = logging.getLogger(__name__)


class DocumentValidator:
    """Infrastructure service for document validation"""
    
    def __init__(self):
        self.ai_docs_path = Path(".cursor/rules/02_AI-DOCS/GENERATE_BY_AI")
        self.validation_patterns = {
            DocumentType.AI_GENERATED: [
                r"\*\*Created By\*\*:\s*(.*Agent)",
                r"\*\*Document ID\*\*:\s*DOC-",
                r"# .+ (Analysis|Report|Guide|Plan)"
            ],
            DocumentType.SYSTEM_CONFIG: [
                r"\.mdc$",
                r"\.json$",
                r"agents\.mdc",
                r"dhafnck_mcp\.mdc"
            ]
        }
        
    def validate_document_creation(self, file_path: str, content: str) -> Dict[str, Any]:
        """Validate document creation with path correction and metadata validation"""
        try:
            path_obj = Path(file_path)
            
            # Detect document type
            doc_type = self._detect_document_type(content)
            
            # Check if path correction is needed
            correction_result = self._check_path_correction(path_obj, doc_type)
            
            # Validate metadata if AI document
            metadata_validation = self._validate_metadata(content, doc_type)
            
            # Update index if needed
            index_update = self._update_index_if_needed(correction_result["corrected_path"], content, doc_type)
            
            # Calculate compliance score
            compliance_score = self._calculate_compliance_score(correction_result, metadata_validation)
            
            return {
                "success": True,
                "document_type": doc_type.value,
                "original_path": str(path_obj),
                "corrected_path": correction_result["corrected_path"],
                "auto_corrected": correction_result["corrected"],
                "metadata_valid": metadata_validation["valid"],
                "index_updated": index_update["updated"],
                "compliance_score": compliance_score,
                "recommendations": correction_result.get("recommendations", [])
            }
            
        except Exception as e:
            logger.error(f"Document validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "compliance_score": 0.0
            }
    
    def _detect_document_type(self, content: str) -> DocumentType:
        """Detect document type based on content patterns"""
        for doc_type, patterns in self.validation_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return doc_type
        return DocumentType.USER_CREATED
    
    def _check_path_correction(self, path_obj: Path, doc_type: DocumentType) -> Dict[str, Any]:
        """Check if path correction is needed"""
        if doc_type == DocumentType.AI_GENERATED:
            if not str(path_obj).startswith(str(self.ai_docs_path)):
                corrected_path = self.ai_docs_path / path_obj.name
                return {
                    "corrected": True,
                    "corrected_path": str(corrected_path),
                    "reason": "AI document auto-corrected to designated folder",
                    "recommendations": [
                        f"AI-generated documents should be placed in {self.ai_docs_path}",
                        "Auto-correction applied for compliance"
                    ]
                }
        
        return {
            "corrected": False,
            "corrected_path": str(path_obj),
            "reason": "No correction needed"
        }
    
    def _validate_metadata(self, content: str, doc_type: DocumentType) -> Dict[str, Any]:
        """Validate document metadata"""
        if doc_type != DocumentType.AI_GENERATED:
            return {"valid": True, "reason": "Non-AI document, metadata not required"}
        
        required_fields = ["Document ID", "Created By", "Date"]
        found_fields = []
        
        for field in required_fields:
            if f"**{field}**:" in content:
                found_fields.append(field)
        
        missing_fields = set(required_fields) - set(found_fields)
        
        return {
            "valid": len(missing_fields) == 0,
            "found_fields": found_fields,
            "missing_fields": list(missing_fields),
            "compliance_percentage": (len(found_fields) / len(required_fields)) * 100
        }
    
    def _update_index_if_needed(self, file_path: str, content: str, doc_type: DocumentType) -> Dict[str, Any]:
        """Update index.json if needed"""
        if doc_type != DocumentType.AI_GENERATED:
            return {"updated": False, "reason": "Non-AI document, index update not needed"}
        
        try:
            index_path = self.ai_docs_path / "index.json"
            
            # Ensure directory exists
            self.ai_docs_path.mkdir(parents=True, exist_ok=True)
            
            # Load existing index
            if index_path.exists():
                with open(index_path, 'r') as f:
                    index_data = json.load(f)
            else:
                index_data = {"documents": [], "last_updated": None}
            
            # Extract document info
            doc_info = self._extract_document_info(file_path, content)
            
            # Check if document already exists in index
            existing_doc = next((doc for doc in index_data["documents"] if doc["file_path"] == file_path), None)
            
            if existing_doc:
                # Update existing entry
                existing_doc.update(doc_info)
                action = "updated"
            else:
                # Add new entry
                index_data["documents"].append(doc_info)
                action = "added"
            
            # Update timestamp
            index_data["last_updated"] = datetime.now().isoformat()
            
            # Write back to index
            with open(index_path, 'w') as f:
                json.dump(index_data, f, indent=2)
            
            return {
                "updated": True,
                "action": action,
                "document_count": len(index_data["documents"])
            }
            
        except Exception as e:
            logger.error(f"Index update failed: {e}")
            return {"updated": False, "error": str(e)}
    
    def _extract_document_info(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract document information for index"""
        # Extract metadata using regex
        doc_id_match = re.search(r'\*\*Document ID\*\*:\s*([^\n]+)', content)
        created_by_match = re.search(r'\*\*Created By\*\*:\s*([^\n]+)', content)
        title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        
        return {
            "file_path": file_path,
            "document_id": doc_id_match.group(1).strip() if doc_id_match else "Unknown",
            "title": title_match.group(1).strip() if title_match else Path(file_path).stem,
            "created_by": created_by_match.group(1).strip() if created_by_match else "Unknown Agent",
            "size_bytes": len(content),
            "created_at": datetime.now().isoformat(),
            "checksum": hashlib.md5(content.encode()).hexdigest()
        }
    
    def _calculate_compliance_score(self, correction_result: Dict[str, Any], 
                                  metadata_validation: Dict[str, Any]) -> float:
        """Calculate overall compliance score"""
        score = 100.0
        
        # Deduct for path correction needed
        if correction_result["corrected"]:
            score -= 10.0  # 10% penalty for incorrect path
        
        # Deduct for missing metadata
        if not metadata_validation["valid"]:
            metadata_score = metadata_validation.get("compliance_percentage", 0)
            score = score * (metadata_score / 100)
        
        return max(0.0, score)