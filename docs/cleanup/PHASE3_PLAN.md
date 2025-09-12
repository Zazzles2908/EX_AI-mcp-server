# Phase 3: Archive-first Cleanup Plan

This plan follows the Cleanup Prompt. All removals are staged into `archive/` first, and can be restored.

## Guiding principles
- Backwards compatible: no schema changes
- Archive-first: do not delete code immediately
- Reversible: provide a restore manifest and script
- Small, safe batches

## Archive directories
- `archive/consensus_legacy/`
- `archive/assessment_legacy/`
- `archive/schemas_legacy/`
- `archive/templates_legacy/`
- `archive/config_legacy/`
- `archive/error_legacy/`
- `archive/tools_legacy/`
- `archive/monitoring_legacy/`

## Candidates to archive (first pass)
- Consensus legacy duplicates (older variants of consensus schema/templates)
- Assessment infrastructure superseded by agentic expert-analysis path
- Duplicated schema builders and prompt templates
- Redundant error utilities replaced by ResilientErrorHandler
- Unused/verbose tool description duplication and dead branches

## Process per batch
1) Dry-run move (list) with cleanup script
2) Archive files into `archive/<category>/`
3) Commit with message `chore(cleanup): archive <batch_name>`
4) Optional: after validation, run delete mode to remove archived files

## Restore process
- Use the manifest entries for a batch to restore files back to their original paths

## Next steps
- Author the manifest JSON
- Implement the cleanup script with dry-run, archive, delete, and restore modes
- Prepare the initial batch (consensus legacy and assessment infra)


## Initial batches to populate

- consensus_legacy:
  - assessments/json/*consensus.json error snapshots related to legacy required findings
- assessment_legacy:
  - assessments/json/*.kimi.json and *.glm.json artifacts from earlier analysis runs
- schemas_templates:
  - any duplicated/obsolete schema builders or templates once identified


## Final plan and task tree (derived from 5 docs)

- Consensus legacy cleanup
  - [x] Inventory errors snapshots under assessments/json/*consensus.json
  - [x] Add to manifest (consensus_legacy)
  - [ ] Archive and optionally delete originals after backup
- Assessment infra cleanup
  - [x] Inventory *.kimi.json and *.glm.json under assessments/json
  - [x] Add to manifest (assessment_legacy)
  - [ ] Archive and optionally delete originals after backup
- Schemas/templates cleanup
  - [ ] Inventory duplicated/obsolete schema builders and templates
  - [ ] Add to manifest (schemas_templates)
  - [ ] Archive and optionally delete originals after backup
- Error/config legacy cleanup
  - [ ] Identify and add obsolete error utilities and config entries replaced by flags
  - [ ] Add to manifest (error_legacy, config_legacy)
  - [ ] Archive and optionally delete originals after backup
- Monitoring/log artifacts cleanup
  - [x] Inventory log artifacts
  - [x] Add to manifest (monitoring_legacy)
  - [ ] Archive and optionally delete originals after backup

Notes:
- Feature flags remain default OFF; no schema/API changes
- Archive-first process, restore supported per batch
