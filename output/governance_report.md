# Clinical Trial Data Governance Report (21 CFR Part 11)

> All figures below come directly from running `python run_all.py` on simulated trial governance data stored in a SQLite database (`data/trial_governance.db`). Nothing is hardcoded.

## Overall audit trail completeness

**2119 of 2134 records (99.30%)** have a complete audit trail (a logged creation event, plus a logged update event for every recorded modification). This is the core 21 CFR Part 11 §11.10(e) requirement: a secure, computer-generated, time-stamped audit trail for every create/modify event on an electronic record.

## Audit trail completeness by study

| Study | Records | Complete | % Complete |
|---|---|---|---|
| STUDY-01 | 292 | 289 | 98.97% |
| STUDY-02 | 362 | 360 | 99.45% |
| STUDY-03 | 268 | 267 | 99.63% |
| STUDY-04 | 248 | 247 | 99.60% |
| STUDY-05 | 384 | 381 | 99.22% |
| STUDY-06 | 259 | 257 | 99.23% |
| STUDY-07 | 321 | 318 | 99.06% |

## Records missing a complete audit trail (remediation list)

**15 records** across the portfolio are missing a complete audit trail entry and are flagged for remediation review:

| Record ID | Study | Type | Modifications | Create entries logged | Update entries logged |
|---|---|---|---|---|---|
| REC-000136 | STUDY-01 | subject_visit | 0 | 0 | 0 |
| REC-000145 | STUDY-01 | subject_visit | 0 | 0 | 0 |
| REC-000196 | STUDY-01 | subject_visit | 2 | 0 | 1 |
| REC-000352 | STUDY-02 | lab_result | 1 | 0 | 0 |
| REC-000589 | STUDY-02 | adverse_event | 0 | 0 | 0 |
| REC-000756 | STUDY-03 | subject_visit | 0 | 0 | 0 |
| REC-000952 | STUDY-04 | adverse_event | 0 | 0 | 0 |
| REC-001177 | STUDY-05 | subject_visit | 2 | 0 | 1 |
| REC-001344 | STUDY-05 | subject_visit | 1 | 0 | 0 |
| REC-001493 | STUDY-05 | adverse_event | 2 | 0 | 1 |
| REC-001614 | STUDY-06 | subject_visit | 0 | 0 | 0 |
| REC-001759 | STUDY-06 | lab_result | 0 | 0 | 0 |
| REC-001824 | STUDY-07 | lab_result | 1 | 0 | 0 |
| REC-001885 | STUDY-07 | adverse_event | 3 | 0 | 2 |
| REC-002071 | STUDY-07 | lab_result | 2 | 0 | 1 |

## 21 CFR Part 11 compliance documentation

**Mean 100.0%** of required compliance documentation items present across studies; **7 of 7 studies** have all required items on file (electronic signature policy, access control policy, record retention policy, audit trail review procedure, system validation documentation).

| Study | Items present | Items required | % Present |
|---|---|---|---|
| STUDY-01 | 5 | 5 | 100.0% |
| STUDY-02 | 5 | 5 | 100.0% |
| STUDY-03 | 5 | 5 | 100.0% |
| STUDY-04 | 5 | 5 | 100.0% |
| STUDY-05 | 5 | 5 | 100.0% |
| STUDY-06 | 5 | 5 | 100.0% |
| STUDY-07 | 5 | 5 | 100.0% |

## Figures

- `output/figures/audit_trail_completeness_by_study.png`
- `output/figures/missing_audit_trail_by_study.png`
- `output/figures/compliance_documentation_heatmap.png`
