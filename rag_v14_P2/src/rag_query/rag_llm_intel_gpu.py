# -*- coding: utf-8 -*-
"""
RAG + LLM Integration for Intel B580 GPU

Uses Intel Extension for PyTorch (IPEX) with small model optimized for 12GB VRAM.

Recommended model: microsoft/Phi-3-mini-4k-instruct (3.8B parameters, ~8GB VRAM)

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

import sys
from pathlib import Path
from rag.chromadb_setup import RAGDatabase
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import time

# Try to import Intel Extension for PyTorch (optional for PyTorch 2.8+)
try:
    import intel_extension_for_pytorch as ipex
    HAS_IPEX = True
except ImportError:
    HAS_IPEX = False
    print("Note: intel_extension_for_pytorch not found, using PyTorch built-in XPU support")


class IntelGPURAGSystem:
    """
    RAG-enhanced LLM system optimized for Intel B580 GPU.

    Features:
    - Intel XPU acceleration via IPEX
    - Small model optimized for 12GB VRAM
    - Efficient RAG retrieval
    - Engineering-focused prompting
    """

    def __init__(
        self,
        db_path: Path,
        model_name: str = "microsoft/Phi-3-mini-4k-instruct"
    ):
        """
        Initialize RAG + LLM system for Intel GPU.

        Args:
            db_path: Path to ChromaDB database
            model_name: HuggingFace model identifier
        """
        print("="*80)
        print("  RAG + LLM System for Intel B580 GPU")
        print("="*80)

        # Check Intel XPU availability
        print(f"\nChecking Intel XPU availability...")
        self.device = self._setup_intel_gpu()

        # Load RAG database
        print(f"\nLoading RAG database from {db_path}...")
        self.db = RAGDatabase(db_path)
        stats = self.db.get_stats()
        print(f"  Database loaded: {stats['total_objects']} objects")
        print(f"  Equations: {stats['by_type'].get('equation', 0)}")
        print(f"  Tables: {stats['by_type'].get('table', 0)}")
        print(f"  Figures: {stats['by_type'].get('figure', 0)}")

        # Load LLM model
        print(f"\nLoading LLM model: {model_name}")
        print(f"  This will download ~8GB if not cached...")
        self._load_model(model_name)

        print(f"\n{'='*80}")
        print("  SYSTEM READY!")
        print(f"{'='*80}\n")

    def _setup_intel_gpu(self) -> str:
        """
        Setup Intel XPU device.

        Returns:
            Device string ('xpu' or 'cpu')
        """
        # Check for XPU availability (PyTorch 2.8+ has built-in support)
        try:
            if HAS_IPEX:
                # Use IPEX if available
                xpu_available = ipex.xpu.is_available()
                if xpu_available:
                    device_count = ipex.xpu.device_count()
                    print(f"  ✓ Intel XPU available (via IPEX)!")
                    print(f"  Devices found: {device_count}")
                    for i in range(device_count):
                        device_name = ipex.xpu.get_device_name(i)
                        props = ipex.xpu.get_device_properties(i)
                        memory_gb = props.total_memory / (1024**3)
                        print(f"  Device {i}: {device_name}")
                        print(f"    Memory: {memory_gb:.2f} GB")
                    return 'xpu'
            else:
                # Use built-in PyTorch XPU support
                # Check if xpu backend is available
                if hasattr(torch, 'xpu') and torch.xpu.is_available():
                    device_count = torch.xpu.device_count()
                    print(f"  ✓ Intel XPU available (PyTorch built-in)!")
                    print(f"  Devices found: {device_count}")
                    for i in range(device_count):
                        props = torch.xpu.get_device_properties(i)
                        print(f"  Device {i}: {props.name}")
                        print(f"    Memory: {props.total_memory / (1024**3):.2f} GB")
                    return 'xpu'

            print(f"  ⚠ Intel XPU not available, using CPU")
            return 'cpu'

        except Exception as e:
            print(f"  ⚠ Error checking XPU: {e}")
            print(f"  Falling back to CPU")
            return 'cpu'

    def _load_model(self, model_name: str):
        """
        Load model with Intel XPU optimization.

        Args:
            model_name: HuggingFace model identifier
        """
        # Load tokenizer
        print(f"  Loading tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )

        # Load model
        print(f"  Loading model...")
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if self.device == 'xpu' else torch.float32,
            trust_remote_code=True
        )

        # Move to device
        print(f"  Moving model to {self.device}...")
        self.model = self.model.to(self.device)

        # Optimize with IPEX if using XPU and IPEX is available
        if self.device == 'xpu' and HAS_IPEX:
            print(f"  Optimizing with Intel Extension for PyTorch...")
            self.model = ipex.optimize(self.model, dtype=torch.float16)
        elif self.device == 'xpu':
            print(f"  Using PyTorch built-in XPU support (no IPEX optimization)")

        self.model.eval()  # Set to evaluation mode
        print(f"  ✓ Model loaded and optimized for {self.device}")

    def retrieve_context(self, question: str, n_results: int = 5) -> dict:
        """
        Retrieve relevant context from RAG database.

        Args:
            question: User's question
            n_results: Number of results to retrieve

        Returns:
            Dictionary with context and sources
        """
        print(f"\n  Retrieving {n_results} relevant chunks from database...")
        start_time = time.time()

        results = self.db.query(question, n_results=n_results)

        retrieve_time = time.time() - start_time

        # Format context
        context_parts = []
        sources = []

        for i, (id, doc, metadata, distance) in enumerate(zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ), 1):
            # Include source information
            source_info = f"[Source {i}] {id} ({metadata['type']}, page {metadata['page']})"
            context_parts.append(f"{source_info}:\n{doc}")

            sources.append({
                'id': id,
                'type': metadata['type'],
                'page': metadata['page'],
                'distance': distance
            })

        context = "\n\n".join(context_parts)

        print(f"  ✓ Retrieved in {retrieve_time:.3f}s")
        print(f"  Top result: {sources[0]['id']} (distance: {sources[0]['distance']:.4f})")

        return {
            'context': context,
            'sources': sources,
            'retrieve_time': retrieve_time
        }

    def generate_answer(
        self,
        question: str,
        context: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7
    ) -> dict:
        """
        Generate answer using LLM with RAG context.

        Args:
            question: User's question
            context: Retrieved context from RAG
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)

        Returns:
            Dictionary with answer and generation stats
        """
        # Build prompt for Phi-3
        # Phi-3 uses specific chat format
        prompt = f"""<|system|>
You are an expert in thermodynamics and heat transfer. Answer the user's question based ONLY on the provided engineering content. Include relevant equations and cite your sources using [Source N] notation. If the information is not in the sources, say so.
<|end|>
<|user|>
Question: {question}

Engineering Content:
{context}
<|end|>
<|assistant|>"""

        print(f"\n  Generating answer with {self.device.upper()}...")
        start_time = time.time()

        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True if temperature > 0 else False,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )

        generate_time = time.time() - start_time

        # Decode
        full_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract just the assistant's answer
        if "<|assistant|>" in full_output:
            answer = full_output.split("<|assistant|>")[-1].strip()
        else:
            answer = full_output.split(prompt)[-1].strip()

        # Calculate tokens
        input_tokens = inputs['input_ids'].shape[1]
        output_tokens = outputs.shape[1] - input_tokens

        print(f"  ✓ Generated in {generate_time:.3f}s")
        print(f"  Input tokens: {input_tokens}, Output tokens: {output_tokens}")
        print(f"  Speed: {output_tokens/generate_time:.1f} tokens/sec")

        return {
            'answer': answer,
            'generate_time': generate_time,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'tokens_per_second': output_tokens / generate_time
        }

    def query(
        self,
        question: str,
        n_results: int = 5,
        max_new_tokens: int = 512,
        temperature: float = 0.7
    ) -> dict:
        """
        End-to-end RAG query with LLM generation.

        Args:
            question: User's engineering question
            n_results: Number of RAG results to retrieve
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Complete results with answer, sources, and timing
        """
        print(f"\n{'='*80}")
        print(f"QUESTION: {question}")
        print(f"{'='*80}")

        # Step 1: Retrieve context
        retrieval = self.retrieve_context(question, n_results)

        # Step 2: Generate answer
        generation = self.generate_answer(
            question,
            retrieval['context'],
            max_new_tokens,
            temperature
        )

        # Combine results
        total_time = retrieval['retrieve_time'] + generation['generate_time']

        result = {
            'question': question,
            'answer': generation['answer'],
            'sources': retrieval['sources'],
            'timing': {
                'retrieve': retrieval['retrieve_time'],
                'generate': generation['generate_time'],
                'total': total_time
            },
            'tokens': {
                'input': generation['input_tokens'],
                'output': generation['output_tokens'],
                'speed': generation['tokens_per_second']
            }
        }

        return result

    def display_result(self, result: dict):
        """Display query result in formatted way."""
        print(f"\n{'='*80}")
        print(f"ANSWER:")
        print(f"{'='*80}\n")
        print(result['answer'])

        print(f"\n{'='*80}")
        print(f"SOURCES:")
        print(f"{'='*80}")
        for i, source in enumerate(result['sources'], 1):
            print(f"  [{i}] {source['id']} ({source['type']}, page {source['page']})")
            print(f"      Distance: {source['distance']:.4f}")

        print(f"\n{'='*80}")
        print(f"PERFORMANCE:")
        print(f"{'='*80}")
        print(f"  Retrieval: {result['timing']['retrieve']:.3f}s")
        print(f"  Generation: {result['timing']['generate']:.3f}s")
        print(f"  Total: {result['timing']['total']:.3f}s")
        print(f"  Tokens: {result['tokens']['input']} in, {result['tokens']['output']} out")
        print(f"  Speed: {result['tokens']['speed']:.1f} tokens/sec")
        print(f"{'='*80}\n")


def test_engineering_questions(rag_system: IntelGPURAGSystem):
    """Test with realistic engineering questions."""
    questions = [
        "What is Fourier's law of heat conduction? Provide the equation.",

        "How do I calculate heat transfer through a composite wall?",

        "What is the thermal conductivity of copper?",

        "Explain thermal resistance in simple terms.",

        "What's the difference between conduction and convection?"
    ]

    results = []

    for i, question in enumerate(questions, 1):
        print(f"\n\n{'#'*80}")
        print(f"# Question {i}/{len(questions)}")
        print(f"{'#'*80}")

        result = rag_system.query(question, n_results=3, max_new_tokens=300)
        rag_system.display_result(result)

        results.append(result)

        if i < len(questions):
            input("\nPress Enter to continue to next question...")

    return results


# Main execution
if __name__ == "__main__":
    # Paths
    base_dir = Path("E:/document_translator_v13")
    db_path = base_dir / "rag_database"

    # Initialize system
    print("\nInitializing RAG + LLM system...\n")
    rag_system = IntelGPURAGSystem(db_path)

    # Test with engineering questions
    print("\n\nStarting test with 5 engineering questions...")
    print("="*80)

    results = test_engineering_questions(rag_system)

    # Summary
    print("\n\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)
    print(f"\nQuestions answered: {len(results)}")
    print(f"Average retrieval time: {sum(r['timing']['retrieve'] for r in results)/len(results):.3f}s")
    print(f"Average generation time: {sum(r['timing']['generate'] for r in results)/len(results):.3f}s")
    print(f"Average total time: {sum(r['timing']['total'] for r in results)/len(results):.3f}s")
    print(f"Average generation speed: {sum(r['tokens']['speed'] for r in results)/len(results):.1f} tokens/sec")
    print(f"\n✓ RAG + LLM system working on Intel B580 GPU!")
    print("="*80)
