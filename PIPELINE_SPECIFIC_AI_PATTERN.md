# Pipeline-Specific AI Instance Pattern

**Created**: 2025-11-16
**Status**: ✅ EXPERIMENT IN PROGRESS (Table Extraction AI)
**Purpose**: Reduce context overload by dedicating AI instances to specific pipelines

---

## 🎯 THE PROBLEM

### Current Architecture (Before This Pattern)
```
One AI instance with root CLAUDE.md
├── All pipeline context (extraction, RAG, curation, detection)
├── All migration history (v9, v10, v11, v13)
├── All agent implementations
└── All troubleshooting notes

Result: Context overload → forgetting critical details
```

**Symptoms of Context Overload**:
- Forgetting table-specific edge cases
- Confusion between pipelines (equation extraction interfering with table work)
- Difficulty maintaining deep expertise in any one area
- Slower problem-solving due to mental context switching

### Why Vertical Pipelines Were Designed
The entire point of creating **vertical pipelines** was to:
1. Reduce design/implementation scope for each component
2. Keep CLAUDE.md files smaller and focused
3. Allow specialized expertise in specific domains
4. Enable parallel work on different pipelines

**We weren't following this principle at the AI instance level.**

---

## ✅ THE SOLUTION: Pipeline-Specific AI Instances

### New Architecture (After This Pattern)
```
Root AI (Orchestration & Cross-Pipeline)
└── Minimal context about pipeline coordination

Pipeline-Specific AIs (Deep Expertise):
├── Table Extraction AI
│   └── pipelines/rag_ingestion/packages/rag_extraction_v14_P16/CLAUDE.md
│       ├── Table types and edge cases
│       ├── Docling markdown parsing
│       ├── Table-specific test workflows
│       └── NO equation/figure/detection context
│
├── Equation Extraction AI
│   └── pipelines/rag_ingestion/packages/rag_extraction_v14_P16/CLAUDE.md (equations)
│       ├── LaTeX-OCR configurations
│       ├── Equation number pairing
│       └── NO table/figure context
│
├── Detection AI
│   └── pipelines/extraction/packages/detection_v14_P14/CLAUDE.md
│       ├── YOLO model configurations
│       ├── Docling detection settings
│       └── NO extraction agent context
│
└── [More pipeline AIs as needed]
```

---

## 📋 IMPLEMENTATION GUIDE

### Step 1: Identify Pipeline Scope

**Questions to Ask**:
- What is this AI instance responsible for?
- What should it remember deeply?
- What is OUT OF SCOPE?

**Example (Table Extraction AI)**:
- ✅ In Scope: Table types, markdown parsing, extraction edge cases
- ❌ Out of Scope: Equation extraction, v9/v10/v11 history, detection algorithms

### Step 2: Create Pipeline-Specific CLAUDE.md

**Location Pattern**:
```
pipelines/[category]/packages/[package_name]/CLAUDE.md
```

**Examples**:
- `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/CLAUDE.md` (tables)
- `pipelines/extraction/packages/detection_v14_P14/CLAUDE.md` (detection)
- `pipelines/rag_ingestion/packages/rag_v14_P2/CLAUDE.md` (RAG chunking)

### Step 3: Extract Relevant Context

**From Root CLAUDE.md, extract ONLY**:
1. Domain-specific knowledge (e.g., table types, known edge cases)
2. Component-specific implementation details
3. Test workflows for this component
4. Recent bugs/fixes for this component

**Explicitly EXCLUDE**:
- Other pipeline contexts
- Migration history (unless directly relevant)
- Cross-pipeline orchestration (that's root AI's job)
- Unrelated troubleshooting notes

### Step 4: Define AI Scope in CLAUDE.md Header

**Template**:
```markdown
# [Pipeline Name] - AI Instance Memory

**Pipeline**: `[package_name]`
**Component**: [Component Name]
**AI Scope**: [What this AI knows] ONLY

## 🎯 PURPOSE OF THIS AI INSTANCE

This AI instance is **dedicated exclusively** to [domain].

✅ Know: [Specific expertise areas]
❌ NOT: [What to ignore]

**Context Budget**: Small, focused, deep expertise.
```

### Step 5: Update Root CLAUDE.md

**Add reference to pipeline-specific AIs**:
```markdown
## 🤖 PIPELINE-SPECIFIC AI INSTANCES

For deep work in specific pipelines, use dedicated AI instances:
- **Table Extraction**: See `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/CLAUDE.md`
- **Equation Extraction**: [TBD]
- **Detection**: [TBD]
- **RAG Chunking**: [TBD]

Root AI handles cross-pipeline orchestration only.
```

---

## 🧪 EXPERIMENT: Table Extraction AI (First Test)

### Setup
- **Created**: 2025-11-16
- **File**: `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/CLAUDE.md`
- **Scope**: Table extraction ONLY (no equations, figures, or other pipelines)

### Hypothesis
Dedicated AI with focused CLAUDE.md will:
1. Remember table-specific edge cases better
2. Solve table extraction issues faster
3. Not get confused by equation extraction context
4. Maintain deeper expertise in Docling markdown parsing

### Success Metrics
- ✅ AI remembers all 13 table types without prompting
- ✅ AI knows Table 2 failure mode without re-investigation
- ✅ AI doesn't mention equations when discussing tables
- ✅ Faster time-to-solution for table-specific bugs

### Current Status
- **Table 2 Issue**: Docling returns empty markdown (root cause identified)
- **Next Step**: Investigate v13 Docling configuration to understand why it worked
- **Test**: Use dedicated Table Extraction AI for next debugging session

---

## 📊 BENEFITS OF THIS PATTERN

### 1. Reduced Context Switching
- AI doesn't juggle table extraction + equation extraction + detection
- Focuses exclusively on one domain at a time
- Deeper, faster problem-solving

### 2. Better Memory Retention
- Smaller CLAUDE.md = better retention of critical details
- AI remembers "Table 4 has embedded diagrams" without re-reading notes
- Fewer tokens spent on context = more tokens for problem-solving

### 3. Parallel Development
- Multiple pipeline-specific AIs can work simultaneously
- Table AI works on tables while Equation AI works on equations
- No interference between work streams

### 4. Matches Architecture Intent
- Vertical pipelines DESIGNED for this isolation
- Finally using the architecture as intended
- Each AI is a specialist, not a generalist

### 5. Easier Handoffs
- New developer reads ONE focused CLAUDE.md
- Not overwhelmed by entire project history
- Faster onboarding to specific pipeline work

---

## 🚀 EXPANSION PLAN

### Phase 1: Validate with Table Extraction (CURRENT)
- ✅ Created `rag_extraction_v14_P16/CLAUDE.md`
- 🔄 Test with Table 2 debugging
- 📊 Measure success metrics

### Phase 2: Expand to Equation Extraction
If Table AI succeeds:
- Create `rag_extraction_v14_P16/CLAUDE_EQUATIONS.md`
- Dedicated AI for LaTeX-OCR and equation numbering
- Separate from table context

### Phase 3: Expand to Detection Pipeline
- Create `detection_v14_P14/CLAUDE.md`
- YOLO and Docling detection configuration
- Zone creation and metadata

### Phase 4: Expand to All Pipelines
- RAG chunking (`rag_v14_P2/CLAUDE.md`)
- Database curation (`curation_v14_P3/CLAUDE.md`)
- Semantic processing (`semantic_processing_v14_P4/CLAUDE.md`)
- Etc.

### Phase 5: Root AI Refactoring
- Strip root CLAUDE.md down to cross-pipeline orchestration only
- Root AI delegates to pipeline-specific AIs
- Minimal context at root level

---

## 🎯 BEST PRACTICES

### DO:
- ✅ Keep pipeline CLAUDE.md files small (<500 lines ideally)
- ✅ Explicitly list what's OUT OF SCOPE
- ✅ Focus on domain-specific edge cases
- ✅ Update after each bug fix with lessons learned
- ✅ Reference other pipelines by location, don't duplicate

### DON'T:
- ❌ Copy-paste from root CLAUDE.md wholesale
- ❌ Include migration history unless directly relevant
- ❌ Track other pipeline's bugs/issues
- ❌ Try to be comprehensive about entire project

### When to Use Root AI vs Pipeline AI:
- **Root AI**: Cross-pipeline orchestration, migration planning, architecture decisions
- **Pipeline AI**: Deep debugging, implementation details, domain-specific edge cases

---

## 📝 TEMPLATE FOR NEW PIPELINE AIs

See `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/CLAUDE.md` as reference template.

**Sections to Include**:
1. **Purpose** - What this AI is responsible for
2. **Domain Knowledge** - Deep expertise in this area
3. **Current Issues** - Active bugs/work
4. **Technical Implementation** - Code locations, key methods
5. **Testing Workflow** - How to validate changes
6. **Out of Scope** - What NOT to track

---

## 🔬 EVALUATION CRITERIA

After 1 week of using Table Extraction AI, evaluate:

**Context Quality**:
- Does AI remember table edge cases without re-reading?
- Does AI stay focused on tables without context switching?
- Is debugging faster with focused context?

**CLAUDE.md Size**:
- Is pipeline CLAUDE.md staying small (<500 lines)?
- Is it easier to update than root CLAUDE.md?

**Problem Solving**:
- Faster time-to-solution for table bugs?
- Fewer instances of "I forgot about X edge case"?

**If Successful**: Expand to all pipelines
**If Unsuccessful**: Document lessons learned and refine approach

---

## 📖 REFERENCES

- **First Pipeline AI**: `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/CLAUDE.md`
- **Root CLAUDE.md**: `/home/thermodynamics/document_translator_v14/CLAUDE.md` (to be refactored)
- **Experiment Start Date**: 2025-11-16
- **Experiment Owner**: Pipeline architecture team

---

*This pattern is an experiment. Document learnings and iterate based on results.*
