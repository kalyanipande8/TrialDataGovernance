"""
standardize.py

Queries the SQLite governance database (data/trial_governance.db) directly
with SQL (via sqlite3) to compute:

  - a per-record audit-trail-completeness flag (a record is "complete" if it
    has a logged CREATE event and at least as many logged UPDATE events as
    its recorded modification count)
  - per-study audit trail completeness %
  - per-study 21 CFR Part 11 compliance documentation checklist status
    (% of required documentation items present)

Writes the resulting summaries to data/processed/ as CSVs for the
downstream analysis step.
"""

import os
import sqlite3

import pandas as pd

from simulate_trial_records import DB_PATH, REQUIRED_COMPLIANCE_ITEMS

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DIR = os.path.join(PROJECT_DIR, "data", "processed")

RECORD_COMPLETENESS_SQL = """
SELECT
    r.record_id,
    r.study_id,
    r.record_type,
    r.n_modifications,
    r.esignature_status,
    COALESCE(SUM(CASE WHEN a.action = 'CREATE' THEN 1 ELSE 0 END), 0) AS n_create_entries,
    COALESCE(SUM(CASE WHEN a.action = 'UPDATE' THEN 1 ELSE 0 END), 0) AS n_update_entries,
    COUNT(a.audit_id) AS n_audit_entries
FROM records r
LEFT JOIN audit_trail a ON a.record_id = r.record_id
GROUP BY r.record_id, r.study_id, r.record_type, r.n_modifications, r.esignature_status
"""

STUDY_COMPLIANCE_SQL = """
SELECT
    study_id,
    SUM(present) AS n_present,
    COUNT(*) AS n_required
FROM compliance_docs
GROUP BY study_id
"""


def query_record_completeness(conn):
    df = pd.read_sql_query(RECORD_COMPLETENESS_SQL, conn)
    df["audit_trail_complete"] = (df["n_create_entries"] >= 1) & (df["n_update_entries"] >= df["n_modifications"])
    return df


def query_study_compliance(conn):
    df = pd.read_sql_query(STUDY_COMPLIANCE_SQL, conn)
    df["pct_compliance_docs_present"] = 100.0 * df["n_present"] / df["n_required"]
    df["required_items"] = ", ".join(REQUIRED_COMPLIANCE_ITEMS)
    return df


def study_audit_summary(record_df):
    grp = record_df.groupby("study_id").agg(
        n_records=("record_id", "count"),
        n_complete=("audit_trail_complete", "sum"),
    ).reset_index()
    grp["pct_audit_trail_complete"] = 100.0 * grp["n_complete"] / grp["n_records"]
    return grp


def standardize():
    conn = sqlite3.connect(DB_PATH)
    record_df = query_record_completeness(conn)
    compliance_df = query_study_compliance(conn)
    conn.close()

    study_audit_df = study_audit_summary(record_df)

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    record_df.to_csv(os.path.join(PROCESSED_DIR, "record_completeness.csv"), index=False)
    study_audit_df.round(3).to_csv(os.path.join(PROCESSED_DIR, "study_audit_summary.csv"), index=False)
    compliance_df.round(3).to_csv(os.path.join(PROCESSED_DIR, "study_compliance_summary.csv"), index=False)

    return record_df, study_audit_df, compliance_df


def main():
    record_df, study_audit_df, compliance_df = standardize()
    overall_pct = 100.0 * record_df["audit_trail_complete"].sum() / len(record_df)
    print(f"Standardized {len(record_df)} records across {record_df['study_id'].nunique()} studies")
    print(f"  Overall audit trail completeness: {overall_pct:.2f}% "
          f"({int(record_df['audit_trail_complete'].sum())}/{len(record_df)})")
    print(f"  Compliance docs: {compliance_df['pct_compliance_docs_present'].mean():.1f}% mean across studies")
    print("  Wrote data/processed/record_completeness.csv, study_audit_summary.csv, study_compliance_summary.csv")


if __name__ == "__main__":
    main()
