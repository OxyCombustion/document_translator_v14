"""
Shared document types and structures for V9
Common classes used across multiple modules to avoid circular imports
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import gc
import time


class ChunkType(Enum):
    """Types of document chunks"""
    PAGE = "page"
    SECTION = "section"
    IMAGE = "image"
    TABLE = "table"
    TEXT_BLOCK = "text_block"


@dataclass
class DocumentChunk:
    """Lightweight document chunk for processing"""
    chunk_id: str
    chunk_type: ChunkType
    page_number: int
    bbox: Optional[Dict[str, float]] = None  # Bounding box on page
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _content: Optional[Any] = field(default=None, repr=False)
    
    def __init__(self, chunk_id: str, chunk_type: ChunkType, page_number: int, 
                 bbox: Optional[Dict[str, float]] = None, content_hash: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None, content: Optional[Any] = None):
        self.chunk_id = chunk_id
        self.chunk_type = chunk_type
        self.page_number = page_number
        self.bbox = bbox
        self.content_hash = content_hash
        self.metadata = metadata or {}
        self._content = content
    
    @property
    def content(self) -> Any:
        """Lazy content access"""
        if self._content is None:
            self._content = self._load_content()
        return self._content
    
    def _load_content(self) -> Any:
        """Load content from storage - override in subclasses"""
        return self._content
    
    def clear_content(self):
        """Clear content to free memory"""
        self._content = None
        gc.collect()
    
    @property
    def size_bytes(self) -> int:
        """Estimate chunk size in bytes"""
        if self._content is None:
            return 0
        
        if isinstance(self._content, (str, bytes)):
            return len(self._content)
        elif isinstance(self._content, dict):
            import json
            return len(json.dumps(self._content, default=str))
        else:
            return len(str(self._content))


@dataclass
class StreamingResult:
    """Lightweight streaming result"""
    chunk_id: str
    agent_name: str
    confidence: float
    processing_time: float
    result_type: str
    data_summary: Dict[str, Any]  # Summary instead of full data
    full_data_path: Optional[str] = None  # Path to full data if cached
    
    def get_full_data(self) -> Dict[str, Any]:
        """Load full data when needed"""
        if self.full_data_path:
            from pathlib import Path
            import json
            if Path(self.full_data_path).exists():
                with open(self.full_data_path, 'r') as f:
                    return json.load(f)
        return self.data_summary


class PageChunk(DocumentChunk):
    """Specialized chunk for PDF pages"""
    
    def _load_content(self) -> bytes:
        """Load page image content"""
        return self._content


class TextChunk(DocumentChunk):
    """Specialized chunk for text content"""
    
    def _load_content(self) -> str:
        """Load text content"""
        return self._content


class ImageChunk(DocumentChunk):
    """Specialized chunk for image content"""
    
    def _load_content(self):
        """Load image content"""
        if isinstance(self._content, bytes):
            from PIL import Image
            import io
            return Image.open(io.BytesIO(self._content))
        return self._content