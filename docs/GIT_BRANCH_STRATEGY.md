# Git Branch Strategy: v14 Development

**Purpose**: Organize v14 development with safe, structured branching
**Date**: 2025-11-14
**Model**: GitFlow-inspired with phase-based development

---

## 🌳 Branch Structure

```
main                    # Production-ready releases
├── develop             # Integration branch
│   ├── phase-0         # Pre-migration safety (COMPLETE)
│   ├── phase-1         # Foundation & interfaces
│   ├── phase-2         # Pipeline 1 (extraction)
│   ├── phase-3         # Pipeline 2 (RAG)
│   ├── phase-4         # Pipeline 3 (curation)
│   ├── phase-5         # Integration testing
│   └── phase-6         # Production validation
├── feature/*           # Feature branches
├── bugfix/*            # Bug fix branches
└── hotfix/*            # Critical production fixes
```

---

## 📋 Branch Descriptions

### **main** (Production)
**Purpose**: Production-ready code only
**Protection**: ✅ Protected (no direct commits)
**Merge From**: `develop` (after phase completion + validation)
**Merge Strategy**: Squash merge with comprehensive commit message
**Tag Strategy**: Semantic versioning (v14.0.0, v14.1.0, etc.)

**Commit Format**:
```
Release v14.{minor}.{patch}: {Description}

- Feature 1 complete
- Feature 2 complete
- All tests passing
- User validation complete

Phases Included: Phase 0-{N}
Components Migrated: {count}/{total}
```

### **develop** (Integration)
**Purpose**: Integration branch for all development
**Protection**: ⚠️ Semi-protected (PR required)
**Merge From**: phase-*, feature/*, bugfix/*
**Merge Strategy**: Merge commit (preserve history)
**Current Status**: Phase 0 ready for merge

**Merge Requirements**:
- All tests passing
- Code review complete
- Documentation updated
- No merge conflicts

### **phase-*** (Phase Development)
**Purpose**: Dedicated branch for each migration phase
**Naming**: `phase-{0-6}` (corresponds to migration plan phases)
**Lifespan**: Created at phase start, deleted after merge to develop
**Protection**: None (active development)

**Phase Branches**:
- `phase-0`: Pre-migration safety (✅ COMPLETE - ready to merge)
- `phase-1`: Foundation & interfaces (⏸️ pending)
- `phase-2`: Pipeline 1 extraction (⏸️ pending)
- `phase-3`: Pipeline 2 RAG (⏸️ pending)
- `phase-4`: Pipeline 3 curation (⏸️ pending)
- `phase-5`: Integration testing (⏸️ pending)
- `phase-6`: Production validation (⏸️ pending)

**Workflow**:
```bash
# Start new phase
git checkout develop
git pull origin develop
git checkout -b phase-1

# Work on phase
git add .
git commit -m "Phase 1: {Description}"

# Finish phase (when complete)
git checkout develop
git merge phase-1 --no-ff -m "Merge phase-1: Foundation & interfaces complete"
git branch -d phase-1
git push origin develop
```

### **feature/*** (Features)
**Purpose**: Individual feature development within a phase
**Naming**: `feature/{phase}-{feature-name}` (e.g., `feature/1-base-classes`)
**Lifespan**: Short-lived (1-3 days)
**Merge To**: Corresponding phase branch

**Workflow**:
```bash
# Create feature branch from phase branch
git checkout phase-1
git checkout -b feature/1-base-classes

# Work on feature
git add .
git commit -m "Implement BaseExtractionAgent"

# Finish feature
git checkout phase-1
git merge feature/1-base-classes --no-ff
git branch -d feature/1-base-classes
```

### **bugfix/*** (Bug Fixes)
**Purpose**: Fix bugs discovered during development
**Naming**: `bugfix/{issue-number}-{description}` (e.g., `bugfix/42-import-error`)
**Lifespan**: Short-lived (hours to 1 day)
**Merge To**: phase-* or develop

**Workflow**:
```bash
# Create bugfix branch
git checkout develop
git checkout -b bugfix/42-import-error

# Fix bug
git add .
git commit -m "Fix: Import error in BaseAgent"

# Merge back
git checkout develop
git merge bugfix/42-import-error --no-ff
git branch -d bugfix/42-import-error
```

### **hotfix/*** (Production Fixes)
**Purpose**: Critical fixes for production (main branch)
**Naming**: `hotfix/v14.{minor}.{patch+1}` (e.g., `hotfix/v14.0.1`)
**Lifespan**: Immediate (hours)
**Merge To**: main AND develop

**Workflow**:
```bash
# Create hotfix from main
git checkout main
git checkout -b hotfix/v14.0.1

# Fix critical bug
git add .
git commit -m "Hotfix: Critical import error"

# Merge to main
git checkout main
git merge hotfix/v14.0.1 --no-ff
git tag v14.0.1

# Merge to develop
git checkout develop
git merge hotfix/v14.0.1 --no-ff

# Delete hotfix branch
git branch -d hotfix/v14.0.1
```

---

## 📊 Current Status (Phase 0)

### **Branches Created**
```bash
git branch -a
  develop       # ✅ Created, empty
* main          # ✅ Current, has first commit (64c4c5d)
  phase-0       # ✅ Created, empty
```

### **Next Steps**

1. **Merge Phase 0 Work to phase-0 Branch**:
   ```bash
   git checkout phase-0
   git cherry-pick 64c4c5d  # First commit with foundation
   # Add Phase 0 completion work
   git add docs/
   git commit -m "Phase 0: Pre-migration safety complete

   - Component audit complete (329 v13 + 10 v12)
   - Component migration mapping (339 components)
   - Configuration migration mapping (13 configs)
   - Documentation migration mapping (187 docs)
   - Migration safety checklist
   - Git branch strategy (this document)
   - Validation script

   Status: Phase 0 100% complete, ready for user approval"
   ```

2. **Merge phase-0 to develop**:
   ```bash
   git checkout develop
   git merge phase-0 --no-ff -m "Merge phase-0: Pre-migration safety complete"
   ```

3. **Tag Phase 0 Completion**:
   ```bash
   git tag v14.0.0-phase0
   ```

4. **Create phase-1 Branch**:
   ```bash
   git checkout develop
   git checkout -b phase-1
   ```

---

## 🔒 Branch Protection Rules

### **main Branch**
```yaml
protection:
  required_status_checks:
    strict: true
    contexts:
      - continuous-integration
      - tests-passing
  required_pull_request_reviews:
    required_approving_review_count: 1
  enforce_admins: false
  restrictions: null
```

### **develop Branch**
```yaml
protection:
  required_status_checks:
    strict: true
    contexts:
      - tests-passing
  required_pull_request_reviews:
    required_approving_review_count: 1
  enforce_admins: false
```

---

## 📝 Commit Message Convention

### **Format**
```
<type>(<scope>): <subject>

<body>

<footer>
```

### **Types**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance (dependencies, build, etc.)

### **Examples**

**Feature**:
```
feat(extraction): Add bidirectional equation extractor

Implement equation extractor that handles numbers before OR after
mathematical content. Includes scoring algorithm and multi-line support.

Migrated from v12 (17K). Tested on Chapter 4 PDF.
```

**Bug Fix**:
```
fix(rag): Import error in BaseAnalyzer

Fixed circular import between BaseAnalyzer and Intelligence modules.
Updated import to use TYPE_CHECKING guard.

Closes #42
```

**Documentation**:
```
docs(readme): Update installation instructions

Added Python 3.11+ requirement and pip install -e . instructions
for all three pipelines.
```

**Phase Completion**:
```
chore(phase-0): Pre-migration safety complete

Phase 0 deliverables:
- Component audit (329 v13 + 10 v12 = 339 total)
- Component migration mapping
- Configuration migration mapping (13 configs)
- Documentation migration mapping (187 docs)
- Migration safety checklist
- Git branch strategy
- Validation script

Status: 100% complete, ready for Phase 1
```

---

## 🔄 Workflow Examples

### **Typical Phase Development**

```bash
# 1. Start phase
git checkout develop
git pull origin develop
git checkout -b phase-1

# 2. Create feature branches as needed
git checkout -b feature/1-base-classes
# ... work ...
git checkout phase-1
git merge feature/1-base-classes --no-ff

# 3. Regular commits during phase
git add .
git commit -m "feat(common): Implement BaseExtractionAgent"

# 4. Finish phase (when all tasks complete)
# Run tests
pytest
# Run validation
python tools/validate_phase1.py
# Get user approval

# 5. Merge to develop
git checkout develop
git merge phase-1 --no-ff -m "Merge phase-1: Foundation & interfaces complete"

# 6. Tag completion
git tag v14.0.0-phase1

# 7. Create next phase
git checkout -b phase-2
```

### **Bug Fix During Development**

```bash
# Discovered bug in phase-2
git checkout phase-2
git checkout -b bugfix/import-error

# Fix bug
# ... work ...
git add .
git commit -m "fix(extraction): Import error in YOLO detector"

# Merge back to phase
git checkout phase-2
git merge bugfix/import-error --no-ff
git branch -d bugfix/import-error
```

---

## 📊 Git History Visualization

**Expected git graph after Phase 0-1**:
```
* (main) Release v14.0.0: Foundation complete
|\
| * (develop) Merge phase-1: Foundation & interfaces
| |\
| | * (phase-1) feat(common): Utilities complete
| | * feat(common): Interfaces complete
| | * feat(common): Base classes complete
| |/
| * Merge phase-0: Pre-migration safety
| |\
| | * (phase-0) Phase 0: Validation script
| | * Phase 0: Git branch strategy
| | * Phase 0: Safety checklist
| | * Phase 0: Docs migration mapping
| | * Phase 0: Config migration mapping
| | * Phase 0: Component migration mapping
| |/
| * Initial commit: Foundation setup
|/
* (initial) Empty repository
```

---

## ✅ Phase 0.12 Complete

**Status**: Git branch strategy established
**Branches Created**: main, develop, phase-0
**Next**: Phase 0.13 (Validation script)

---

**Created**: 2025-11-14
**Status**: ✅ Complete - Branch strategy ready for v14 development
