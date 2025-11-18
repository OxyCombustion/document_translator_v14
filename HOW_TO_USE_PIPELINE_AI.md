# How to Use Pipeline-Specific AI Instances - Quick Reference

**For**: Developers and AI instances working on v14 pipelines
**Purpose**: Know when to use focused pipeline AI vs root AI

---

## 🚀 QUICK DECISION TREE

```
Are you working on:

┌─ Cross-pipeline orchestration?
│  └─ Use ROOT AI (/home/thermodynamics/document_translator_v14/)
│
├─ Table extraction bugs/features?
│  └─ Use TABLE AI (pipelines/rag_ingestion/packages/rag_extraction_v14_P16/)
│
├─ Equation extraction bugs/features?
│  └─ Use EQUATION AI (pipelines/rag_ingestion/packages/rag_extraction_v14_P16/)
│      Read: CLAUDE_EQUATIONS.md
│
├─ Figure extraction bugs/features?
│  └─ Use FIGURE AI (pipelines/rag_ingestion/packages/rag_extraction_v14_P16/)
│      Read: CLAUDE_FIGURES.md
│
├─ Text extraction/semantic chunking/RAG preparation?
│  └─ Use TEXT AI (pipelines/rag_ingestion/packages/rag_v14_P2/)
│      Read: CLAUDE_TEXT.md
│
├─ Detection configuration (YOLO/Docling)?
│  └─ Use DETECTION AI (pipelines/extraction/packages/detection_v14_P14/)
│      [TBD - create CLAUDE.md]
│
└─ Other pipeline-specific work?
   └─ Check if pipeline has CLAUDE*.md, otherwise use ROOT AI
```

---

## 📍 WHEN TO USE ROOT AI

**Use root AI for**:
- Planning v13→v14 migration phases
- Cross-pipeline coordination
- Architecture decisions affecting multiple pipelines
- Creating new pipelines
- Git operations affecting entire project

**Root AI working directory**: `/home/thermodynamics/document_translator_v14/`

---

## 📍 WHEN TO USE PIPELINE AI

**Use pipeline AI for**:
- Debugging extraction agents (tables, equations, figures)
- Tuning detection parameters (YOLO, Docling)
- Fixing pipeline-specific bugs
- Implementing pipeline features
- Writing pipeline tests

**Pipeline AI working directories**:
- Table Extraction: `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/` (CLAUDE.md)
- Equation Extraction: `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/` (CLAUDE_EQUATIONS.md)
- Figure Extraction: `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/` (CLAUDE_FIGURES.md)
- Text/RAG Chunking: `pipelines/rag_ingestion/packages/rag_v14_P2/` (CLAUDE_TEXT.md)
- Detection: `pipelines/extraction/packages/detection_v14_P14/` [TBD]

---

## 🔄 HOW TO SWITCH BETWEEN AIs

### Option 1: Claude Code Projects (Recommended)
Create separate Claude Code projects:
- **Project "Document Translator - Root"**: Root directory
- **Project "Document Translator - Table Extraction"**: `rag_extraction_v14_P16/` directory
- **Project "Document Translator - Detection"**: `detection_v14_P14/` directory

Switch between projects to automatically load correct context.

### Option 2: Explicit Context Loading
Tell Claude Code which CLAUDE.md to use:
```
"Load context from pipelines/rag_ingestion/packages/rag_extraction_v14_P16/CLAUDE.md
and work on table extraction issues only."
```

### Option 3: Directory Navigation
Navigate to pipeline directory before starting work:
```bash
cd pipelines/rag_ingestion/packages/rag_extraction_v14_P16
```
Then tell Claude: "Work in current directory, load local CLAUDE.md"

---

## ✅ VERIFICATION: Am I Using the Right AI?

**Ask yourself**:
- Does this AI know about [my specific pipeline]? → Check CLAUDE.md scope
- Is this AI bringing up unrelated pipelines? → Wrong AI, switch
- Am I getting "I don't have context about X"? → Might need root AI

**Red flags you're using wrong AI**:
- Table AI talking about equations → Wrong AI
- Root AI debugging Docling markdown parsing → Wrong AI, use Table AI
- Detection AI discussing RAG chunking → Wrong AI

---

## 📋 PIPELINE AI CHECKLIST

Before starting work with pipeline AI:

1. **Verify AI scope**:
   - Read "PURPOSE OF THIS AI INSTANCE" in CLAUDE.md
   - Confirm your work is in scope

2. **Check "Out of Scope" section**:
   - If your task is listed there, use different AI

3. **Use pipeline-specific tests**:
   - Each pipeline AI knows its own test workflows
   - Don't ask root AI to run pipeline-specific tests

4. **Stay focused**:
   - If AI brings up unrelated topics, remind it of scope
   - Example: "Focus on tables only, ignore equations"

---

## 🎯 BENEFITS YOU'LL NOTICE

**With Pipeline AI**:
- ✅ Faster debugging (AI remembers edge cases)
- ✅ No context switching confusion
- ✅ Deeper expertise in specific domain
- ✅ Smaller context = better memory

**With Root AI**:
- ✅ Cross-pipeline coordination
- ✅ Architecture-level decisions
- ✅ Migration planning
- ✅ Big picture perspective

---

## 🚨 COMMON MISTAKES

### Mistake 1: Using Root AI for Pipeline Debugging
**Wrong**:
```
Root AI: "Debug table markdown parsing in rag_extraction_v14_P16"
```

**Right**:
```
Table AI: "Debug table markdown parsing" (already in correct directory)
```

### Mistake 2: Using Pipeline AI for Cross-Pipeline Work
**Wrong**:
```
Table AI: "Coordinate detection zones with extraction agents"
```

**Right**:
```
Root AI: "Coordinate detection_v14_P14 zones with rag_extraction_v14_P16"
```

### Mistake 3: Asking Pipeline AI About Other Pipelines
**Wrong**:
```
Table AI: "How does equation extraction work?"
```

**Right**:
```
Root AI: "Show me equation extraction overview"
or
Equation AI: "Explain equation extraction implementation"
```

---

## 📖 CURRENT STATUS (2025-11-16)

### ✅ Implemented Pipeline AIs:
- **Table Extraction AI** - `rag_extraction_v14_P16/CLAUDE.md`
- **Equation Extraction AI** - `rag_extraction_v14_P16/CLAUDE_EQUATIONS.md`
- **Figure Extraction AI** - `rag_extraction_v14_P16/CLAUDE_FIGURES.md`
- **Text/RAG Chunking AI** - `rag_v14_P2/CLAUDE_TEXT.md`

### 🔄 Coming Soon:
- **Detection AI** - `detection_v14_P14/CLAUDE.md`
- **Curation AI** - `curation_v14_P3/CLAUDE.md`
- **Semantic Processing AI** - `semantic_processing_v14_P4/CLAUDE.md`
- **Relationship Detection AI** - `relationship_detection_v14_P5/CLAUDE.md`

### ✅ Always Available:
- **Root AI** - `/home/thermodynamics/document_translator_v14/CLAUDE.md`

### 📁 Status File Communication System:
- `rag_extraction_v14_P16/STATUS_EQUATIONS.json` - Equation extraction status
- `rag_extraction_v14_P16/STATUS_FIGURES.json` - Figure extraction status
- `rag_extraction_v14_P16/STATUS_TABLES.json` - Table extraction status
- `rag_v14_P2/STATUS_TEXT.json` - Text/RAG preparation status

---

## 🔗 RELATED DOCUMENTATION

- **Pattern Guide**: `PIPELINE_SPECIFIC_AI_PATTERN.md` (full explanation)
- **Table AI Memory**: `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/CLAUDE.md`
- **Root AI Memory**: `CLAUDE.md` (this directory)

---

*Use the right tool for the job - pipeline AI for depth, root AI for breadth.*
