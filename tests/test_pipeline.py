import os
import sqlite3
import sys

import pandas as pd
import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import simulate_trial_records as sim  # noqa: E402
import standardize  # noqa: E402
import governance_analysis as ga  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def ensure_pipeline_ran():
    sim.simulate()
    standardize.standardize()
    ga.main()
    yield


def test_total_record_count_is_2134():
    conn = sqlite3.connect(sim.DB_PATH)
    n = pd.read_sql_query("SELECT COUNT(*) AS n FROM records", conn)["n"].iloc[0]
    conn.close()
    assert n == 2134


def test_seven_studies_present():
    conn = sqlite3.connect(sim.DB_PATH)
    n_studies = pd.read_sql_query("SELECT COUNT(DISTINCT study_id) AS n FROM records", conn)["n"].iloc[0]
    conn.close()
    assert n_studies == 7


def test_audit_trail_completeness_near_99_3_percent():
    record_df = pd.read_csv(os.path.join(standardize.PROCESSED_DIR, "record_completeness.csv"))
    pct = 100.0 * record_df["audit_trail_complete"].sum() / len(record_df)
    # Target from the resume bullet is 99.3%; allow a reasonable band.
    assert 98.5 <= pct <= 99.9


def test_compliance_documentation_is_100_percent_across_all_studies():
    compliance_df = pd.read_csv(os.path.join(standardize.PROCESSED_DIR, "study_compliance_summary.csv"))
    assert len(compliance_df) == 7
    assert (compliance_df["pct_compliance_docs_present"] == 100.0).all()


def test_referential_integrity_between_records_and_audit_trail():
    """Every audit_trail.record_id must reference an existing records.record_id."""
    conn = sqlite3.connect(sim.DB_PATH)
    orphans = pd.read_sql_query(
        """
        SELECT a.record_id FROM audit_trail a
        LEFT JOIN records r ON a.record_id = r.record_id
        WHERE r.record_id IS NULL
        """,
        conn,
    )
    conn.close()
    assert len(orphans) == 0


def test_every_record_with_multiple_modifications_has_at_least_two_audit_rows():
    """Injected sanity check: any record modified more than once must have
    >=2 audit_trail rows logged for it (a CREATE plus at least one UPDATE,
    or multiple UPDATEs), UNLESS it is one of the deliberately-injected
    incomplete-audit-trail records."""
    conn = sqlite3.connect(sim.DB_PATH)
    records = pd.read_sql_query("SELECT record_id, n_modifications FROM records", conn)
    audit_counts = pd.read_sql_query(
        "SELECT record_id, COUNT(*) AS n_audit_rows FROM audit_trail GROUP BY record_id", conn
    )
    conn.close()

    merged = records.merge(audit_counts, on="record_id", how="left")
    merged["n_audit_rows"] = merged["n_audit_rows"].fillna(0)

    record_df = pd.read_csv(os.path.join(standardize.PROCESSED_DIR, "record_completeness.csv"))
    complete_ids = set(record_df.loc[record_df["audit_trail_complete"], "record_id"])

    multiply_modified = merged[merged["n_modifications"] > 1]
    complete_and_multiply_modified = multiply_modified[multiply_modified["record_id"].isin(complete_ids)]

    assert len(complete_and_multiply_modified) > 0
    assert (complete_and_multiply_modified["n_audit_rows"] >= 2).all()


def test_missing_audit_records_list_matches_incomplete_flag_count():
    record_df = pd.read_csv(os.path.join(standardize.PROCESSED_DIR, "record_completeness.csv"))
    missing_df = ga.missing_audit_records(record_df)
    assert len(missing_df) == int((~record_df["audit_trail_complete"]).sum())
