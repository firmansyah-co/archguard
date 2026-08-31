# Integrating ArchGuard with Hermes Agent

ArchGuard is engineered from the ground up to pair with **Hermes Agent** (`hermes-agent`) to provide non-bypassable guardrails for autonomous coding loops.

---

## 1. Why ArchGuard with Hermes?

Large Language Models working on multi-step software tasks can suffer from architectural drift:
- Introducing inline hardcoded `#hex` colors instead of design tokens.
- Leaking SQL queries directly into API controllers.
- Dropping temporary scratchpad scripts into the project root directory.
- Forgetting to synchronize specifications and contracts.

ArchGuard acts as a deterministic static verification gate that catches these regressions before commits or PRs are created.

---

## 2. Installing and Updating the Hermes Skill

### Automatic Symlink Synchronization via CLI

Run `archguard update` or `archguard update --self` from any terminal:
```bash
archguard update --self
```
This automatically ensures `~/.hermes/skills/engineering/archguard` symlinks directly to the ArchGuard repository's skill folder.

### Manual Installation (Fallback)

Copy or link the skill into your active Hermes profile:


```bash
# For default profile
mkdir -p ~/.hermes/skills/archguard
cp -r skills/archguard/* ~/.hermes/skills/archguard/

# For a specific profile (e.g. head-software)
mkdir -p ~/.hermes/profiles/head-software/skills/archguard
cp -r skills/archguard/* ~/.hermes/profiles/head-software/skills/archguard/
```

Verify skill visibility:
```bash
hermes skills
```

---

## 3. Autonomous Execution in Agent Loops

Autonomous agents can invoke the standalone runner script to get machine-readable JSON feedback:

```bash
python3 skills/archguard/scripts/run_archguard.py --json
```

Sample JSON response returned:

```json
{
  "passed": false,
  "total_errors": 1,
  "total_warnings": 0,
  "total_files_checked": 42,
  "results": [
    {
      "validator_name": "layer_validator",
      "standard": "ISO/IEC/IEEE 42010:2022",
      "passed": false,
      "violations": [
        {
          "rule_id": "ISO-42010-001",
          "standard": "ISO/IEC/IEEE 42010:2022",
          "severity": "error",
          "message": "Layer 'api' imports forbidden module/layer 'repository'.",
          "file_path": "backend/src/api/user.py",
          "line_number": 4,
          "remediation_hint": "Decouple 'api' from 'repository'. Route data access through the Service layer."
        }
      ]
    }
  ]
}
```

The agent reads `remediation_hint` and self-corrects the code before proceeding.
