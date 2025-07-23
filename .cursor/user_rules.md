# 🧠 Memory‑Bank FIRST – Non‑Negotiable
**At the start of EVERY task** execute memory.mdc
Do so after **EVERY message turn**.

If any file missing/out‑of‑date → ask user, then create/update before coding.

---

## Workflow Modes
| Mode          | Trigger                               | Rule File     |
|---------------|---------------------------------------|---------------|
| **Plan**      | New feature / scope change            | plan.mdc      |
| **Implement** | Approved checklist item or debugging  | implement.mdc |

Switch modes explicitly; finish current checklist item before switching.

---

## Code Discipline
* full type hints, docstrings, inline descriptions.
* Secrets via `constants.py` (env vars), never hard‑coded.

---

## Documentation Discipline
After completing a task:
1. Tick checklist in **plan.md** if applicable.  
2. Briefly summarise result in “Completed” section  
3. Note reusable insight or errors (if any) to "Known Issues" into **progress.md** subsection  

---

## Human‑in‑Loop Checkpoints
* STOP and request approval for:
  - New or revised plan
  - Refactor touching >10 % of codebase
