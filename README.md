# TrialDataGovernance: Clinical Trial Data Governance with Audit Trails

Implements a data governance pipeline for clinical trial eCRF-style records
(subject visit data, lab results, adverse event reports) across multiple
studies, backed by a **SQL (SQLite) database** with a relational schema for
records and their audit trail, in the spirit of **21 CFR Part 11** electronic
records / electronic signature requirements.

> **Disclaimer:** This is a portfolio/demo project. All trial records, users,
> timestamps, and audit-trail events are **synthetically simulated** by
> `simulate_trial_records.py`. No real subject, site, study, or employer data
> is used. The compliance documentation checklist is a simulated example of
> the kind of policy documentation a Part 11 system inventory would track,
> not an actual regulatory filing.

## What it does

1. **`simulate_trial_records.py`** simulates **2,134 eCRF records** (subject
   visits, lab results, adverse events) across **7 studies**, each carrying
   standard governance metadata: creator/modifier user ID, creation and
   last-modification timestamps, electronic signature status, and a
   change-history audit-trail entry for every create/modify event (who /
   when / what field changed / old -> new value). Loads everything into a
   SQLite database, `data/trial_governance.db`, with three tables:

   ```
   records          one row per eCRF record (record_id, study_id, record_type,
                     subject_id, created_by/at, last_modified_by/at,
                     n_modifications, esignature_status)
   audit_trail       one row per audit event (audit_id, record_id FK, study_id,
                     action [CREATE/UPDATE], changed_by, changed_at,
                     field_changed, old_value, new_value) -- one-to-many
                     against records
   compliance_docs   one row per (study_id, required doc item) 21 CFR Part 11
                     compliance-documentation checklist entry
   ```

   A small, deliberately injected subset of records (15 of 2,134) are missing
   a proper audit-trail entry for a creation or modification event --
   simulating the real-world governance gaps a Part 11 audit would flag for
   remediation. Every study's compliance-documentation checklist (electronic
   signature policy, access control policy, record retention policy, audit
   trail review procedure, system validation documentation) is complete.

2. **`standardize.py`** queries the SQLite database directly with **SQL**
   (via `sqlite3` / `pandas.read_sql_query`) to compute a per-record
   audit-trail-completeness flag, per-study completeness %, and the
   compliance-documentation checklist status per study, writing the results
   to `data/processed/*.csv` for downstream analysis.

3. **`governance_analysis.py`** computes the governance/regulatory-audit
   view:
   - Overall audit trail completeness %
   - Which records/studies are missing an audit trail entry (a remediation
     list)
   - 21 CFR Part 11 compliance documentation % by study
   - A governance summary suitable for a quality/regulatory audience

   Produces 3 figures in `output/figures/` and `output/governance_report.md`.

4. **`run_all.py`** runs the whole pipeline.

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_all.py
pytest -q
```

## Results

_All numbers below are copied directly from an actual run of `python
run_all.py` - nothing is hardcoded. Fixed random seed (42) makes them
reproducible._

- **2,134 records** simulated across **7 studies**, generating **3,442 audit
  trail rows** and **35 compliance_docs rows** (5 required items x 7
  studies).
- **Overall audit trail completeness: 99.30% (2,119 / 2,134 records)** --
  matching the resume bullet's target exactly with this run's seed and
  parameters.
- **15 records** are missing a complete audit trail and are listed by
  record ID / study / type in `output/governance_report.md` for
  remediation.
- **21 CFR Part 11 compliance documentation: 100.0%** across all 7 studies
  (7 of 7 studies have all 5 required documentation items on file).

### Audit trail completeness by study

| Study | Records | Complete | % Complete |
|---|---|---|---|
| STUDY-01 | 292 | 289 | 98.97% |
| STUDY-02 | 362 | 360 | 99.45% |
| STUDY-03 | 268 | 267 | 99.63% |
| STUDY-04 | 248 | 247 | 99.60% |
| STUDY-05 | 384 | 381 | 99.22% |
| STUDY-06 | 259 | 257 | 99.23% |
| STUDY-07 | 321 | 318 | 99.06% |

### Compliance documentation by study

All 7 studies: **5 / 5 required items present (100.0%)**.

(Full remediation list of the 15 incomplete records is in
`output/governance_report.md`; this table is a snapshot, re-running
reproduces it exactly.)

## Figures

- `output/figures/audit_trail_completeness_by_study.png`
- `output/figures/missing_audit_trail_by_study.png`
- `output/figures/compliance_documentation_heatmap.png`

## Project structure

```
simulate_trial_records.py   # 2,134 records x 7 studies -> data/trial_governance.db (SQLite)
standardize.py               # SQL queries -> per-record/per-study completeness -> data/processed/
governance_analysis.py       # governance stats, figures, report -> output/
run_all.py                   # orchestrates the full pipeline
tests/test_pipeline.py       # pytest checks incl. referential integrity + injected sanity check
```

## Tech stack

- Python 3
- **SQLite** (via `sqlite3` / `pandas.read_sql_query`) as the SQL backing
  store for governed trial records and the audit trail
- pandas / numpy for data simulation and wrangling
- matplotlib for figures
- pytest
