# Project Governance Structure

This directory manages collaboration between Antigravity (planning/specification) and Claude (implementation).

---

## Directory Structure

```
.project_governance/
├── specs/              # Antigravity writes these (Read-Only for Claude)
│   ├── active_spec.md
│   └── archive/
├── reports/            # Claude writes these (Read-Only for Antigravity)
│   └── implementation_report_[date].md
└── knowledge_graph/    # Antigravity maintains high-level architectural decisions here
    ├── architecture_decisions.md
    └── style_guide.md
```

---

## Workflow

### 1. Specification Phase (Antigravity)

Antigravity creates detailed specifications in:
- **`specs/active_spec.md`** - Current specification for implementation

When a spec is completed, it moves to:
- **`specs/archive/`** - Historical specifications

### 2. Implementation Phase (Claude)

Claude:
1. Reads `specs/active_spec.md`
2. Implements the specified features
3. Documents work in `reports/implementation_report_[date].md`

### 3. Knowledge Maintenance (Antigravity)

Antigravity maintains architectural knowledge in:
- **`knowledge_graph/architecture_decisions.md`** - ADRs (Architecture Decision Records)
- **`knowledge_graph/style_guide.md`** - Coding standards and conventions

Both agents read these to maintain consistency.

---

## Permissions Matrix

| Directory | Antigravity | Claude |
|-----------|-------------|--------|
| `specs/` | ✍️ Write | 👁️ Read |
| `reports/` | 👁️ Read | ✍️ Write |
| `knowledge_graph/` | ✍️ Write | 👁️ Read |

---

## File Naming Conventions

### Specifications
- Active: `active_spec.md`
- Archived: `spec_[feature_name]_[date].md`

### Reports
- Format: `implementation_report_[YYYY-MM-DD].md`
- One report per implementation session

### Knowledge Graph
- `architecture_decisions.md` - ADRs
- `style_guide.md` - Code style and conventions
- Additional files as needed for domain knowledge

---

## Best Practices

### For Antigravity:
- Write clear, actionable specifications
- Include acceptance criteria
- Reference relevant architectural decisions
- Archive completed specs with implementation reports

### For Claude:
- Always read `active_spec.md` before implementing
- Follow guidelines in `knowledge_graph/`
- Document all implementation decisions in reports
- Note any deviations from spec with justification
- Raise questions/blockers clearly in reports

---

## Example Workflow

1. **Antigravity** creates specification:
   ```
   specs/active_spec.md:
   - Feature: Add thermal stress analysis
   - Requirements: [detailed list]
   - Acceptance criteria: [test cases]
   ```

2. **Claude** implements and reports:
   ```
   reports/implementation_report_2025-12-17.md:
   - Implemented thermal stress module
   - Added tests covering all criteria
   - Question: Should we support non-linear materials?
   ```

3. **Antigravity** reviews report and either:
   - Archives spec if complete
   - Updates spec with clarifications
   - Creates new spec for follow-up work

---

## Version Control

- All files in this directory are tracked in git
- Commit messages should reference spec/report being modified
- Never delete archived specs (they're historical record)
