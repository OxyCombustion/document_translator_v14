# -*- coding: utf-8 -*-
"""
Simple RAG + LLM for Intel GPU

Uses simpler, more compatible models for Intel B580.

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
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig
import time


def check_gpu():
    """Check GPU availability"""
    print("Checking GPU availability...")

    if hasattr(torch, 'xpu') and torch.xpu.is_available():
        device_count = torch.xpu.device_count()
        print(f"✓ Intel XPU available!")
        print(f"  Devices: {device_count}")
        for i in range(device_count):
            props = torch.xpu.get_device_properties(i)
            print(f"  Device {i}: {props.name}")
            print(f"  Memory: {props.total_memory / (1024**3):.2f} GB")
        return 'xpu'
    else:
        print(f"⚠ Intel XPU not available, using CPU")
        return 'cpu'


def simple_rag_query(question: str, db: RAGDatabase, n_results: int = 3):
    """Simple RAG retrieval"""
    print(f"\n{'='*80}")
    print(f"Question: {question}")
    print(f"{'='*80}\n")

    print(f"Retrieving {n_results} relevant sources...")
    start_time = time.time()

    results = db.query(question, n_results=n_results)
    retrieve_time = time.time() - start_time

    # Format context
    context_parts = []
    for i, (id, doc, metadata, distance) in enumerate(zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ), 1):
        print(f"  [{i}] {id} ({metadata['type']}, page {metadata['page']}) - distance: {distance:.4f}")
        context_parts.append(f"[Source {i}] {doc}")

    context = "\n\n".join(context_parts)

    print(f"\n✓ Retrieved in {retrieve_time:.3f}s")
    print(f"\n{'-'*80}")
    print("RETRIEVED CONTENT:")
    print(f"{'-'*80}")
    for i, part in enumerate(context_parts, 1):
        print(f"\n[Source {i}]:")
        print(part[:200] + "..." if len(part) > 200 else part)

    return context, results


def test_with_tinyllama(db: RAGDatabase, device: str):
    """Test with TinyLlama (small, fast, compatible)"""
    model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

    print(f"\n{'='*80}")
    print(f"Loading TinyLlama 1.1B model...")
    print(f"{'='*80}\n")

    # Load model
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if device == 'xpu' else torch.float32,
    )

    print(f"Moving to {device}...")
    model = model.to(device)
    model.eval()

    print(f"✓ Model ready on {device}!\n")

    # Test questions
    questions = [
        "What is Fourier's law of heat conduction?",
        "How do I calculate heat transfer through a composite wall?",
        "What is thermal conductivity?"
    ]

    for question in questions:
        # Retrieve context
        context, results = simple_rag_query(question, db, n_results=3)

        # Build prompt
        prompt = f"""<|system|>
You are an expert in thermodynamics. Answer based on the provided sources. Cite sources as [Source N].
<|user|>
Question: {question}

Sources:
{context}
<|assistant|>"""

        print(f"\n{'='*80}")
        print(f"Generating answer with {device.upper()}...")
        print(f"{'='*80}\n")

        start_time = time.time()

        inputs = tokenizer(prompt, return_tensors="pt").to(device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id
            )

        generate_time = time.time() - start_time

        answer = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract assistant answer
        if "<|assistant|>" in answer:
            answer = answer.split("<|assistant|>")[-1].strip()

        print(f"ANSWER:")
        print(f"{'-'*80}")
        print(answer)
        print(f"\n{'-'*80}")
        print(f"Generation time: {generate_time:.2f}s")
        print(f"Tokens/sec: {(outputs.shape[1] - inputs['input_ids'].shape[1])/generate_time:.1f}")
        print(f"{'='*80}\n")

        input("\nPress Enter for next question...")


# Main execution
if __name__ == "__main__":
    print("\n" + "="*80)
    print("  SIMPLE RAG + LLM TEST (Intel B580 GPU)")
    print("="*80 + "\n")

    # Check GPU
    device = check_gpu()

    # Load database
    print(f"\nLoading RAG database...")
    db_path = Path("E:/document_translator_v13/rag_database")
    db = RAGDatabase(db_path)

    stats = db.get_stats()
    print(f"✓ Database loaded: {stats['total_objects']} objects\n")

    # Test with TinyLlama
    test_with_tinyllama(db, device)

    print("\n✓ Test complete!")
