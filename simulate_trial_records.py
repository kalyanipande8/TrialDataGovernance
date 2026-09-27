"""
simulate_trial_records.py

Simulates clinical trial eCRF-style data records (subject visit data, lab
results, adverse event reports) across 7 studies, each carrying the
governance metadata a 21 CFR Part 11 compliant system requires:

  - creator user ID + creation timestamp
  - modifier user ID + last-modification timestamp (for modified records)
  - electronic signature status
  - a change-history / audit-trail entry for every create/modify event,
    capturing who / when / what field changed / old -> new value

Loads everything into a SQLite database (data/trial_governance.db) with a
relational schema:

  records       one row per eCRF record (2,134 total across 7 studies)
  audit_trail   one row per audit event; one-to-many against records
  compliance_docs  one row per (study, required documentation item), for the
                   21 CFR Part 11 compliance documentation checklist

A small, deliberately injected subset of records (target ~15 of 2,134, i.e.
~99.3% audit trail completeness) are missing a proper audit-trail entry -
simulating the real-world governance gaps a Part 11 audit would flag for
remediation. Every study's compliance documentation checklist is complete
(100%), matching the "100% compliance documentation" claim.

Uses a fixed random seed (numpy).
"""

import os
import sqlite3
from datetime import datetime, timedelta

import numpy as np

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "trial_governance.db")

RANDOM_SEED = 42
N_STUDIES = 7
N_RECORDS_TOTAL = 2134
N_MISSING_AUDIT_TARGET = 15  # -> ~99.3% completeness (2119/2134 = 0.99297)

STUDIES = [f"STUDY-{i:02d}" for i in range(1, N_STUDIES + 1)]

RECORD_TYPES = ["subject_visit", "lab_result", "adverse_event"]
RECORD_TYPE_WEIGHTS = [0.55, 0.30, 0.15]

USERS = [f"USER-{i:03d}" for i in range(1, 26)]  # 25 site/CRA/DM users

CHANGE_FIELDS = {
    "subject_visit": ["visit_date", "vitals_bp_systolic", "vitals_weight_kg", "concomitant_med", "visit_status"],
    "lab_result": ["analyte_value", "unit", "reference_range_flag", "sample_collection_time"],
    "adverse_event": ["ae_severity", "ae_causality", "ae_outcome", "ae_term"],
}

REQUIRED_COMPLIANCE_ITEMS = [
    "electronic_signature_policy",
    "access_control_policy",
    "record_retention_policy",
    "audit_trail_review_procedure",
    "system_validation_documentation",
]

STUDY_START = datetime(2023, 1, 1)


def _random_timestamp(rng, start, end_days):
    offset_seconds = rng.integers(0, end_days * 86400)
    return start + timedelta(seconds=int(offset_seconds))


def simulate():
    rng = np.random.default_rng(RANDOM_SEED)

    # ---- split 2,134 records across 7 studies (unequal enrollment, but deterministic) ----
    study_weights = rng.dirichlet(np.ones(N_STUDIES) * 4.0)
    counts = np.floor(study_weights * N_RECORDS_TOTAL).astype(int)
    counts[-1] += N_RECORDS_TOTAL - counts.sum()  # make totals exact

    records = []
    audit_rows = []
    record_counter = 1
    audit_counter = 1

    # decide, in advance, exactly which global record indices get a broken audit trail
    missing_audit_indices = set(
        rng.choice(N_RECORDS_TOTAL, size=N_MISSING_AUDIT_TARGET, replace=False).tolist()
    )

    global_idx = 0
    for study_id, n_recs in zip(STUDIES, counts):
        study_start = STUDY_START + timedelta(days=int(rng.integers(0, 120)))
        for _ in range(n_recs):
            record_id = f"REC-{record_counter:06d}"
            record_type = rng.choice(RECORD_TYPES, p=RECORD_TYPE_WEIGHTS)
            creator = rng.choice(USERS)
            created_at = _random_timestamp(rng, study_start, 500)

            # number of modifications after creation: mostly 0-1, some 2-3
            n_mods = int(rng.choice([0, 1, 2, 3], p=[0.55, 0.30, 0.10, 0.05]))

            esignature_status = rng.choice(
                ["signed", "signed", "signed", "pending"], p=[0.6, 0.2, 0.1, 0.1]
            )

            last_modified_at = created_at
            last_modifier = creator

            is_broken = global_idx in missing_audit_indices

            # ---- audit trail: creation event ----
            # For "broken" records we simulate the real governance gap: the
            # creation event itself was never logged to the audit trail.
            if not is_broken:
                audit_rows.append({
                    "audit_id": f"AUD-{audit_counter:07d}",
                    "record_id": record_id,
                    "study_id": study_id,
                    "action": "CREATE",
                    "changed_by": creator,
                    "changed_at": created_at.isoformat(sep=" "),
                    "field_changed": None,
                    "old_value": None,
                    "new_value": "initial_entry",
                })
                audit_counter += 1

            ts = created_at
            for mod_i in range(n_mods):
                ts = ts + timedelta(days=int(rng.integers(1, 20)))
                modifier = rng.choice(USERS)
                field = rng.choice(CHANGE_FIELDS[record_type])
                last_modified_at = ts
                last_modifier = modifier

                # For broken records, drop exactly one modification's audit
                # entry (the first one) to simulate an incomplete trail,
                # rather than logging every single change.
                if is_broken and mod_i == 0:
                    continue

                audit_rows.append({
                    "audit_id": f"AUD-{audit_counter:07d}",
                    "record_id": record_id,
                    "study_id": study_id,
                    "action": "UPDATE",
                    "changed_by": modifier,
                    "changed_at": ts.isoformat(sep=" "),
                    "field_changed": field,
                    "old_value": "prev_value",
                    "new_value": "new_value",
                })
                audit_counter += 1

            records.append({
                "record_id": record_id,
                "study_id": study_id,
                "record_type": record_type,
                "subject_id": f"{study_id}-SUBJ-{int(rng.integers(1, 250)):04d}",
                "created_by": creator,
                "created_at": created_at.isoformat(sep=" "),
                "last_modified_by": last_modifier,
                "last_modified_at": last_modified_at.isoformat(sep=" "),
                "n_modifications": n_mods,
                "esignature_status": esignature_status,
            })

            record_counter += 1
            global_idx += 1

    # ---- 21 CFR Part 11 compliance documentation checklist: 100% complete for all 7 studies ----
    compliance_rows = []
    for study_id in STUDIES:
        for item in REQUIRED_COMPLIANCE_ITEMS:
            compliance_rows.append({
                "study_id": study_id,
                "doc_item": item,
                "present": 1,
                "last_reviewed_date": (STUDY_START + timedelta(days=int(rng.integers(30, 400)))).date().isoformat(),
            })

    _write_db(records, audit_rows, compliance_rows)

    n_missing = len(records) - len({a["record_id"] for a in audit_rows if a["action"] == "CREATE"})
    print(f"Simulated {len(records)} trial records across {N_STUDIES} studies")
    print(f"  audit_trail rows: {len(audit_rows)}")
    print(f"  compliance_docs rows: {len(compliance_rows)} ({len(REQUIRED_COMPLIANCE_ITEMS)} items x {N_STUDIES} studies)")
    print(f"  Wrote {DB_PATH}")


def _write_db(records, audit_rows, compliance_rows):
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE records (
            record_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            record_type TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_modified_by TEXT NOT NULL,
            last_modified_at TEXT NOT NULL,
            n_modifications INTEGER NOT NULL,
            esignature_status TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE audit_trail (
            audit_id TEXT PRIMARY KEY,
            record_id TEXT NOT NULL,
            study_id TEXT NOT NULL,
            action TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            field_changed TEXT,
            old_value TEXT,
            new_value TEXT,
            FOREIGN KEY (record_id) REFERENCES records(record_id)
        )
    """)
    cur.execute("""
        CREATE TABLE compliance_docs (
            study_id TEXT NOT NULL,
            doc_item TEXT NOT NULL,
            present INTEGER NOT NULL,
            last_reviewed_date TEXT NOT NULL,
            PRIMARY KEY (study_id, doc_item)
        )
    """)

    cur.executemany(
        "INSERT INTO records VALUES (:record_id, :study_id, :record_type, :subject_id, :created_by, "
        ":created_at, :last_modified_by, :last_modified_at, :n_modifications, :esignature_status)",
        records,
    )
    cur.executemany(
        "INSERT INTO audit_trail VALUES (:audit_id, :record_id, :study_id, :action, :changed_by, "
        ":changed_at, :field_changed, :old_value, :new_value)",
        audit_rows,
    )
    cur.executemany(
        "INSERT INTO compliance_docs VALUES (:study_id, :doc_item, :present, :last_reviewed_date)",
        compliance_rows,
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    simulate()
