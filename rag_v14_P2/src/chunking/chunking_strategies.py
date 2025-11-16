# -*- coding: utf-8 -*-
"""
Chunking Strategies for Engineering Content

Implements intelligent chunking for RAG systems that handles:
- Text with embedded equations, tables, and figures
- Semantic boundary preservation
- Context window optimization
- Multi-modal content representation

Author: Document Translator V11
Date: 2025-01-17
"""

import sys
import os

# MANDATORY UTF-8 SETUP
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class ChunkConfig:
    """Configuration for chunking strategies"""
    target_tokens: int = 512
    max_tokens: int = 768
    min_tokens: int = 256
    overlap_tokens: int = 64
    boundary_type: str = "semantic"  # "semantic" or "fixed"
    include_context: bool = True
    context_tokens: int = 128


@dataclass
class ContentChunk:
    """Represents a chunk of content ready for embedding"""
    chunk_id: str
    chunk_type: str  # "text_only", "text_with_equation", "text_with_table", "text_with_figure"
    text_content: str
    page: int
    section: str

    # Optional embedded objects
    embedded_equations: List[str] = None  # List of equation IDs
    embedded_tables: List[str] = None     # List of table IDs
    embedded_figures: List[str] = None    # List of figure IDs

    # Context
    preceding_context: str = ""
    following_context: str = ""

    # Metadata
    char_count: int = 0
    token_count: int = 0
    keywords: List[str] = None

    def __post_init__(self):
        if self.embedded_equations is None:
            self.embedded_equations = []
        if self.embedded_tables is None:
            self.embedded_tables = []
        if self.embedded_figures is None:
            self.embedded_figures = []
        if self.keywords is None:
            self.keywords = []

        # Calculate counts if not provided
        if self.char_count == 0:
            self.char_count = len(self.text_content)
        if self.token_count == 0:
            # Rough estimate: 1 token ≈ 4 characters for English text
            self.token_count = len(self.text_content) // 4


class EngineeringContentChunker:
    """
    Intelligent chunking for engineering documents with equations, tables, and figures.

    Design Philosophy:
    - Preserve semantic boundaries (don't break mid-concept)
    - Include surrounding context for better retrieval
    - Handle embedded objects (equations, tables, figures) specially
    - Optimize for RAG retrieval effectiveness
    """

    def __init__(self, config: Optional[ChunkConfig] = None):
        """
        Initialize chunker with configuration.

        Args:
            config: ChunkConfig object, uses defaults if None
        """
        self.config = config or ChunkConfig()

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses simple heuristic: ~4 chars per token for English text.
        For production, use tiktoken library for accurate counts.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def find_semantic_boundaries(self, text: str) -> List[int]:
        """
        Find semantic boundaries in text (paragraph breaks, section headers).

        Boundaries are positions where it's safe to split text without
        breaking concepts or sentences.

        Args:
            text: Input text to analyze

        Returns:
            List of character positions that are safe split points
        """
        boundaries = [0]  # Start is always a boundary

        # Find paragraph breaks (double newlines)
        for match in re.finditer(r'\n\n+', text):
            boundaries.append(match.end())

        # Find section headers (lines starting with numbers like "4.1" or "4.1.2")
        for match in re.finditer(r'\n\d+\.\d+(\.\d+)?\s+[A-Z]', text):
            boundaries.append(match.start() + 1)  # After the newline

        # Find sentence boundaries as fallback (period followed by space and capital letter)
        for match in re.finditer(r'\.\s+[A-Z]', text):
            boundaries.append(match.end() - 1)  # Before the capital letter

        boundaries.append(len(text))  # End is always a boundary

        return sorted(set(boundaries))  # Remove duplicates and sort

    def chunk_text_only(
        self,
        text: str,
        page: int,
        section: str,
        start_chunk_id: int = 1
    ) -> List[ContentChunk]:
        """
        Chunk plain text without embedded objects.

        Uses semantic boundaries to avoid breaking concepts.
        Includes overlap between chunks for context continuity.

        Args:
            text: Text to chunk
            page: Page number
            section: Section identifier
            start_chunk_id: Starting ID for chunks

        Returns:
            List of ContentChunk objects
        """
        chunks = []
        boundaries = self.find_semantic_boundaries(text)

        current_start = 0
        chunk_id = start_chunk_id

        while current_start < len(text):
            # Find the best boundary for target token count
            target_end = current_start + (self.config.target_tokens * 4)  # Convert tokens to chars
            max_end = current_start + (self.config.max_tokens * 4)

            # Find the closest boundary within max_tokens
            best_boundary = None
            for boundary in boundaries:
                if current_start < boundary <= max_end:
                    if abs(boundary - target_end) < abs((best_boundary or boundary) - target_end):
                        best_boundary = boundary

            # If no boundary found, use max_end
            if best_boundary is None:
                best_boundary = min(max_end, len(text))

            # Extract chunk text
            chunk_text = text[current_start:best_boundary].strip()

            # Get context (preceding and following)
            preceding_context = ""
            following_context = ""

            if self.config.include_context:
                context_chars = self.config.context_tokens * 4

                # Preceding context
                context_start = max(0, current_start - context_chars)
                if context_start < current_start:
                    preceding_context = text[context_start:current_start].strip()

                # Following context
                context_end = min(len(text), best_boundary + context_chars)
                if best_boundary < context_end:
                    following_context = text[best_boundary:context_end].strip()

            # Create chunk
            chunk = ContentChunk(
                chunk_id=f"chunk_{chunk_id:03d}",
                chunk_type="text_only",
                text_content=chunk_text,
                page=page,
                section=section,
                preceding_context=preceding_context,
                following_context=following_context
            )

            chunks.append(chunk)

            # Move to next chunk with overlap
            overlap_chars = self.config.overlap_tokens * 4
            current_start = max(best_boundary - overlap_chars, best_boundary)
            chunk_id += 1

            # Safety check to prevent infinite loops
            if current_start >= len(text):
                break

        return chunks

    def create_chunk_with_equation(
        self,
        text: str,
        equation_id: str,
        equation_latex: str,
        equation_text_description: str,
        page: int,
        section: str,
        chunk_id: str
    ) -> ContentChunk:
        """
        Create a chunk that includes an equation.

        The chunk text includes:
        1. Surrounding text context
        2. Equation in LaTeX notation
        3. Text description of equation

        Args:
            text: Surrounding text
            equation_id: Equation identifier (e.g., "eq_001")
            equation_latex: LaTeX representation
            equation_text_description: Human-readable description
            page: Page number
            section: Section identifier
            chunk_id: Chunk identifier

        Returns:
            ContentChunk with embedded equation
        """
        # Build combined text for embedding
        combined_text = f"{text}\n\nEquation: {equation_latex}\n\n{equation_text_description}"

        chunk = ContentChunk(
            chunk_id=chunk_id,
            chunk_type="text_with_equation",
            text_content=combined_text,
            page=page,
            section=section,
            embedded_equations=[equation_id]
        )

        return chunk

    def create_chunk_with_table(
        self,
        text: str,
        table_id: str,
        table_summary: str,
        sample_rows: str,
        page: int,
        section: str,
        chunk_id: str
    ) -> ContentChunk:
        """
        Create a chunk that includes a table.

        The chunk text includes:
        1. Surrounding text context
        2. Table summary (e.g., "Table 7 shows thermal properties of 45 materials")
        3. Sample rows for context

        Args:
            text: Surrounding text
            table_id: Table identifier (e.g., "table_007")
            table_summary: Human-readable summary
            sample_rows: First few rows in markdown format
            page: Page number
            section: Section identifier
            chunk_id: Chunk identifier

        Returns:
            ContentChunk with embedded table
        """
        # Build combined text for embedding
        combined_text = f"{text}\n\n{table_summary}\n\nSample data:\n{sample_rows}"

        chunk = ContentChunk(
            chunk_id=chunk_id,
            chunk_type="text_with_table",
            text_content=combined_text,
            page=page,
            section=section,
            embedded_tables=[table_id]
        )

        return chunk

    def create_chunk_with_figure(
        self,
        text: str,
        figure_id: str,
        caption: str,
        visual_description: str,
        page: int,
        section: str,
        chunk_id: str
    ) -> ContentChunk:
        """
        Create a chunk that includes a figure.

        The chunk text includes:
        1. Surrounding text context
        2. Figure caption
        3. Visual description (e.g., "Circuit diagram showing...")

        Args:
            text: Surrounding text
            figure_id: Figure identifier (e.g., "fig_004")
            caption: Figure caption
            visual_description: Description of visual content
            page: Page number
            section: Section identifier
            chunk_id: Chunk identifier

        Returns:
            ContentChunk with embedded figure
        """
        # Build combined text for embedding
        combined_text = f"{text}\n\nFigure: {caption}\n\n{visual_description}"

        chunk = ContentChunk(
            chunk_id=chunk_id,
            chunk_type="text_with_figure",
            text_content=combined_text,
            page=page,
            section=section,
            embedded_figures=[figure_id]
        )

        return chunk

    def optimize_chunk_size(self, chunk: ContentChunk) -> ContentChunk:
        """
        Optimize chunk size by trimming or padding.

        Ensures chunks are within min_tokens and max_tokens bounds.

        Args:
            chunk: ContentChunk to optimize

        Returns:
            Optimized ContentChunk
        """
        if chunk.token_count < self.config.min_tokens:
            # Chunk too small - add more context
            # (Implementation would fetch more surrounding text)
            pass

        if chunk.token_count > self.config.max_tokens:
            # Chunk too large - trim at semantic boundary
            boundaries = self.find_semantic_boundaries(chunk.text_content)
            target_char = self.config.max_tokens * 4

            # Find closest boundary
            best_boundary = min(boundaries, key=lambda b: abs(b - target_char))
            chunk.text_content = chunk.text_content[:best_boundary].strip()
            chunk.char_count = len(chunk.text_content)
            chunk.token_count = self.estimate_tokens(chunk.text_content)

        return chunk


class ChunkQualityAnalyzer:
    """
    Analyzes chunk quality for RAG effectiveness.

    Quality metrics:
    - Coherence: Does the chunk contain complete concepts?
    - Context: Is there sufficient context for understanding?
    - Size: Is the chunk within optimal token range?
    - Embedding readiness: Is it suitable for embedding?
    """

    @staticmethod
    def calculate_coherence(chunk: ContentChunk) -> float:
        """
        Calculate semantic coherence score.

        Higher score = more complete concepts, fewer broken sentences.

        Args:
            chunk: ContentChunk to analyze

        Returns:
            Coherence score (0.0 to 1.0)
        """
        text = chunk.text_content

        # Check for broken sentences at boundaries
        score = 1.0

        # Penalize if starts mid-sentence (lowercase letter)
        if text and text[0].islower():
            score -= 0.2

        # Penalize if ends mid-sentence (no ending punctuation)
        if text and text[-1] not in '.!?':
            score -= 0.2

        # Reward complete paragraphs
        if '\n\n' in text:
            score += 0.1

        return max(0.0, min(1.0, score))

    @staticmethod
    def calculate_context_quality(chunk: ContentChunk) -> float:
        """
        Calculate context quality score.

        Higher score = better surrounding context for understanding.

        Args:
            chunk: ContentChunk to analyze

        Returns:
            Context quality score (0.0 to 1.0)
        """
        score = 0.5  # Base score

        # Reward preceding context
        if chunk.preceding_context:
            score += 0.25

        # Reward following context
        if chunk.following_context:
            score += 0.25

        return score

    @staticmethod
    def calculate_size_optimality(chunk: ContentChunk, config: ChunkConfig) -> float:
        """
        Calculate how close chunk size is to optimal.

        Optimal size is target_tokens ± 20%.

        Args:
            chunk: ContentChunk to analyze
            config: ChunkConfig with target sizes

        Returns:
            Size optimality score (0.0 to 1.0)
        """
        target = config.target_tokens
        actual = chunk.token_count

        # Calculate deviation from target
        deviation = abs(actual - target) / target

        # Perfect score at target, linear decay to 0 at 50% deviation
        score = max(0.0, 1.0 - (deviation * 2))

        return score

    @staticmethod
    def is_embedding_ready(chunk: ContentChunk) -> bool:
        """
        Check if chunk is ready for embedding.

        Requirements:
        - Non-empty text
        - Within token bounds
        - Contains meaningful content (not just whitespace)

        Args:
            chunk: ContentChunk to check

        Returns:
            True if ready for embedding
        """
        if not chunk.text_content or not chunk.text_content.strip():
            return False

        if chunk.token_count == 0:
            return False

        # Check for meaningful content (at least 10 words)
        word_count = len(chunk.text_content.split())
        if word_count < 10:
            return False

        return True


# Example usage and testing
if __name__ == "__main__":
    # Example text with multiple paragraphs
    sample_text = """
    Heat transfer by conduction occurs when molecular energy is exchanged through
    direct contact. The fundamental relationship governing conductive heat transfer
    is Fourier's law.

    The rate of heat transfer is proportional to the temperature gradient and the
    cross-sectional area perpendicular to the gradient. This relationship forms the
    basis for analyzing steady-state conduction problems.

    For one-dimensional steady-state conduction with constant thermal conductivity,
    the heat transfer rate can be calculated using a simplified form of Fourier's law.
    """

    # Create chunker with default config
    chunker = EngineeringContentChunker()

    # Chunk the text
    chunks = chunker.chunk_text_only(
        text=sample_text,
        page=2,
        section="4.1 Conduction",
        start_chunk_id=1
    )

    # Analyze quality
    analyzer = ChunkQualityAnalyzer()

    print("=== Chunking Results ===\n")
    for chunk in chunks:
        print(f"Chunk ID: {chunk.chunk_id}")
        print(f"Type: {chunk.chunk_type}")
        print(f"Characters: {chunk.char_count}")
        print(f"Tokens (estimated): {chunk.token_count}")
        print(f"Coherence: {analyzer.calculate_coherence(chunk):.2f}")
        print(f"Context Quality: {analyzer.calculate_context_quality(chunk):.2f}")
        print(f"Embedding Ready: {analyzer.is_embedding_ready(chunk)}")
        print(f"\nText:\n{chunk.text_content[:200]}...")
        print("\n" + "="*60 + "\n")
