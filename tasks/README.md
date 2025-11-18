# Task Communication System

**Purpose**: Enable AI-to-AI task delegation and coordination in multi-AI architecture

**Pattern**: Orchestrator AI creates task files → Pipeline AIs execute → Report completion

---

## 📋 Task File Format

### JSON Schema

```json
{
  "task_id": "TASK_XXX",
  "title": "Short descriptive title",
  "assigned_to": "extraction_ai | rag_ai | database_ai | shared_ai",
  "delegated_by": "orchestrator",
  "created_at": "2025-11-17T20:00:00Z",
  "status": "pending | in_progress | completed | blocked",
  "priority": "critical | high | medium | low",

  "specification": {
    "description": "Detailed task description",
    "affected_packages": ["package1", "package2"],
    "affected_pipelines": ["extraction", "rag"],
    "deliverables": [
      "Specific deliverable 1",
      "Specific deliverable 2"
    ],
    "acceptance_criteria": [
      "Criterion 1",
      "Criterion 2"
    ]
  },

  "dependencies": {
    "blocks": ["TASK_002", "TASK_003"],
    "blocked_by": ["TASK_000"],
    "related": ["TASK_004"]
  },

  "context_updates": [
    "Contract change: Added 'annotations' field",
    "Performance requirement: Must process <100ms"
  ],

  "completion_criteria": [
    "All tests pass",
    "Documentation updated",
    "Contract validated"
  ],

  "progress_log": [
    {
      "timestamp": "2025-11-17T20:30:00Z",
      "status": "in_progress",
      "note": "Started implementation"
    }
  ],

  "notes": "Additional context or special instructions"
}
```

---

## 🔄 Task Workflow

### Step 1: Orchestrator Creates Task

**When**: Cross-pipeline coordination needed

**Action**: Orchestrator creates `TASK_XXX_description.json` file

**Example**:
```bash
tasks/TASK_001_add_annotation_extraction.json
```

---

### Step 2: Pipeline AI Executes

**When**: Pipeline AI picks up assigned task

**Actions**:
1. Read task file
2. Update status to "in_progress"
3. Implement deliverables
4. Run tests
5. Update documentation

**Status Updates**:
```json
{
  "status": "in_progress",
  "progress_log": [
    {
      "timestamp": "2025-11-17T21:00:00Z",
      "status": "in_progress",
      "note": "AnnotationExtractor class created"
    },
    {
      "timestamp": "2025-11-17T21:30:00Z",
      "status": "in_progress",
      "note": "Tests passing, documentation updated"
    }
  ]
}
```

---

### Step 3: Completion & Handoff

**When**: Pipeline AI completes task

**Actions**:
1. Update status to "completed"
2. Add completion note
3. Notify Orchestrator (update task file)

**Orchestrator Reviews**:
- Validates completion criteria met
- Checks integration with other tasks
- Coordinates next steps

---

## 📝 Task Naming Convention

### Format
```
TASK_{ID}_{pipeline}_{description}.json
```

### Examples
- `TASK_001_extraction_add_annotations.json`
- `TASK_002_rag_handle_annotations.json`
- `TASK_003_cross_update_contracts.json`

---

## 🎯 Task Types

### Type 1: Single Pipeline Task

**Characteristics**:
- Affects one pipeline only
- No contract changes
- No cross-pipeline dependencies

**Example**:
```json
{
  "task_id": "TASK_001",
  "title": "Fix YOLO detection accuracy",
  "assigned_to": "extraction_ai",
  "affected_pipelines": ["extraction"]
}
```

---

### Type 2: Cross-Pipeline Task

**Characteristics**:
- Affects multiple pipelines
- May require contract changes
- Coordination needed

**Example**:
```json
{
  "task_id": "TASK_005",
  "title": "Add annotations support",
  "assigned_to": "orchestrator",
  "affected_pipelines": ["extraction", "rag"],
  "dependencies": {
    "blocks": ["TASK_006_extraction", "TASK_007_rag"]
  }
}
```

**Orchestrator** creates subtasks:
- `TASK_006_extraction_implement_annotations.json`
- `TASK_007_rag_handle_annotations.json`

---

### Type 3: Architectural Task

**Characteristics**:
- System-wide impact
- Orchestrator handles directly
- May delegate implementation

**Example**:
```json
{
  "task_id": "TASK_010",
  "title": "Add 4th pipeline for exports",
  "assigned_to": "orchestrator",
  "affected_pipelines": ["all"]
}
```

---

## 🚨 Task Status Values

| Status | Meaning | Who Sets |
|--------|---------|----------|
| `pending` | Not started | Orchestrator |
| `in_progress` | Currently being worked on | Pipeline AI |
| `blocked` | Waiting on dependency | Pipeline AI |
| `completed` | Finished successfully | Pipeline AI |
| `cancelled` | No longer needed | Orchestrator |

---

## 📊 Task Priority Levels

| Priority | SLA | Use Case |
|----------|-----|----------|
| `critical` | Immediate | Production bugs, blocking issues |
| `high` | <1 day | Important features, contract changes |
| `medium` | <1 week | Regular features, improvements |
| `low` | Backlog | Nice-to-haves, refactoring |

---

## 🔍 Task Discovery

### For Pipeline AIs

**Check for assigned tasks**:
```bash
ls tasks/TASK_*_extraction_*.json  # Extraction AI
ls tasks/TASK_*_rag_*.json         # RAG AI
ls tasks/TASK_*_database_*.json    # Database AI
ls tasks/TASK_*_shared_*.json      # Shared AI
```

**Or filter by status**:
```bash
grep -l '"status": "pending"' tasks/*.json
grep -l '"assigned_to": "extraction_ai"' tasks/*.json
```

---

### For Orchestrator

**Monitor all tasks**:
```bash
ls tasks/TASK_*.json
```

**Check blocked tasks**:
```bash
grep -l '"status": "blocked"' tasks/*.json
```

**Review completed tasks**:
```bash
grep -l '"status": "completed"' tasks/*.json
```

---

## 💡 Best Practices

### For Orchestrator

1. **Clear Specifications**
   - Detailed task descriptions
   - Explicit deliverables
   - Measurable acceptance criteria

2. **Appropriate Delegation**
   - Assign to correct pipeline AI
   - Consider dependencies
   - Set realistic priorities

3. **Track Progress**
   - Monitor status updates
   - Identify blockers early
   - Coordinate cross-pipeline tasks

---

### For Pipeline AIs

1. **Update Status Promptly**
   - Mark in_progress when starting
   - Add progress log entries
   - Mark completed when done

2. **Follow Completion Criteria**
   - Verify all criteria met
   - Run tests
   - Update documentation

3. **Escalate Blockers**
   - Mark as blocked with reason
   - Notify Orchestrator
   - Suggest solutions

---

## 📁 Directory Structure

```
tasks/
├── README.md (this file)
├── TASK_001_extraction_add_annotations.json
├── TASK_002_rag_handle_annotations.json
├── TASK_003_cross_update_contracts.json
├── completed/
│   └── TASK_000_example_completed.json (archived)
└── templates/
    ├── task_template.json
    └── cross_pipeline_task_template.json
```

---

## 🎯 Example Workflows

See example task files in this directory:
- `TASK_001_extraction_add_annotations.json` - Single pipeline
- `TASK_002_rag_handle_annotations.json` - Coordinated task
- `TASK_003_cross_update_contracts.json` - Cross-pipeline

---

**Status**: Active task communication system
**Version**: 1.0
**Last Updated**: 2025-11-17
