"""
run_all.py

Runs the full pipeline end-to-end:
  1. Simulate 2,134 trial records across 7 studies into a SQLite database
     with a records / audit_trail / compliance_docs schema -> data/trial_governance.db
  2. Query the database with SQL to compute audit-trail-completeness and
     compliance-documentation summaries -> data/processed/
  3. Governance/regulatory analysis, figures, and report -> output/

Run with:  python run_all.py
"""

import simulate_trial_records
import standardize
import governance_analysis


def main():
    print("--- Simulating trial records into SQLite (data/trial_governance.db) ---")
    simulate_trial_records.simulate()

    print("\n--- Standardizing via SQL queries into governance summaries ---")
    standardize.main()

    print("\n--- Governance analysis ---")
    governance_analysis.main()


if __name__ == "__main__":
    main()
