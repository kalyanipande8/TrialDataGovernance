"""
governance_analysis.py

Computes the governance/regulatory-audit view the standardized SQL summaries
enable:

  1. Overall 21 CFR Part 11 audit trail completeness % (target ~99.3%)
  2. Which records/studies are missing a complete audit trail, for
     remediation (a "findings list" a quality/regulatory reviewer would use)
  3. 21 CFR Part 11 compliance documentation % by study (target 100%)
  4. A governance summary suitable for a quality/regulatory audience

Produces:
  - output/figures/audit_trail_completeness_by_study.png
  - output/figures/missing_audit_trail_by_study.png
  - output/figures/compliance_documentation_heatmap.png
  - output/governance_report.md
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from simulate_trial_records import REQUIRED_COMPLIANCE_ITEMS
from standardize import PROCESSED_DIR, standardize

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
FIGURES_DIR = os.path.join(OUTPUT_DIR, "figures")

PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]


def load():
    record_df = pd.read_csv(os.path.join(PROCESSED_DIR, "record_completeness.csv"))
    study_audit_df = pd.read_csv(os.path.join(PROCESSED_DIR, "study_audit_summary.csv"))
    compliance_df = pd.read_csv(os.path.join(PROCESSED_DIR, "study_compliance_summary.csv"))
    return record_df, study_audit_df, compliance_df


def overall_completeness(record_df):
    n_complete = int(record_df["audit_trail_complete"].sum())
    n_total = len(record_df)
    return n_complete, n_total, 100.0 * n_complete / n_total


def missing_audit_records(record_df):
    missing = record_df.loc[~record_df["audit_trail_complete"],
                             ["record_id", "study_id", "record_type", "n_modifications",
                              "n_create_entries", "n_update_entries"]]
    return missing.sort_values(["study_id", "record_id"])


def compliance_heatmap_matrix(conn_free_compliance_df):
    """Rebuild an item x study present/absent matrix from the raw compliance_docs table."""
    import sqlite3
    from simulate_trial_records import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    raw = pd.read_sql_query("SELECT study_id, doc_item, present FROM compliance_docs", conn)
    conn.close()
    pivot = raw.pivot(index="doc_item", columns="study_id", values="present")
    return pivot.reindex(REQUIRED_COMPLIANCE_ITEMS)


def make_figures(study_audit_df, missing_df, compliance_df):
    os.makedirs(FIGURES_DIR, exist_ok=True)

    # Figure 1: audit trail completeness by study (bar)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ordered = study_audit_df.sort_values("study_id")
    ax.bar(ordered["study_id"], ordered["pct_audit_trail_complete"],
           color=PALETTE[: len(ordered)])
    ax.axhline(99.3, color="#e34948", linestyle="--", linewidth=1, label="99.3% target")
    ax.set_ylim(95, 100.5)
    ax.set_ylabel("Audit trail completeness (%)")
    ax.set_title("21 CFR Part 11 audit trail completeness by study")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "audit_trail_completeness_by_study.png"), dpi=150)
    plt.close(fig)

    # Figure 2: missing audit trail records by study (bar count)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    counts = missing_df.groupby("study_id").size().reindex(sorted(study_audit_df["study_id"]), fill_value=0)
    ax.bar(counts.index, counts.values, color=PALETTE[: len(counts)])
    ax.set_ylabel("Records missing complete audit trail (count)")
    ax.set_title("Audit trail gaps by study (remediation list)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "missing_audit_trail_by_study.png"), dpi=150)
    plt.close(fig)

    # Figure 3: compliance documentation checklist heatmap by study
    matrix = compliance_heatmap_matrix(compliance_df)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    im = ax.imshow(matrix.values, cmap="Greens", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(matrix.index)))
    ax.set_yticklabels(matrix.index)
    ax.set_title("21 CFR Part 11 compliance documentation checklist by study")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, "OK" if matrix.values[i, j] == 1 else "MISSING",
                     ha="center", va="center", fontsize=7,
                     color="white" if matrix.values[i, j] == 1 else "black")
    fig.colorbar(im, ax=ax, label="present (1) / missing (0)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "compliance_documentation_heatmap.png"), dpi=150)
    plt.close(fig)


def write_report(record_df, study_audit_df, compliance_df, missing_df):
    n_complete, n_total, overall_pct = overall_completeness(record_df)
    mean_compliance_pct = compliance_df["pct_compliance_docs_present"].mean()
    n_studies_full_compliance = int((compliance_df["pct_compliance_docs_present"] == 100.0).sum())

    lines = [
        "# Clinical Trial Data Governance Report (21 CFR Part 11)",
        "",
        "> All figures below come directly from running `python run_all.py` on simulated "
        "trial governance data stored in a SQLite database "
        "(`data/trial_governance.db`). Nothing is hardcoded.",
        "",
        "## Overall audit trail completeness",
        "",
        f"**{n_complete} of {n_total} records ({overall_pct:.2f}%)** have a complete audit "
        f"trail (a logged creation event, plus a logged update event for every recorded "
        f"modification). This is the core 21 CFR Part 11 §11.10(e) requirement: a "
        f"secure, computer-generated, time-stamped audit trail for every create/modify "
        f"event on an electronic record.",
        "",
        "## Audit trail completeness by study",
        "",
        "| Study | Records | Complete | % Complete |",
        "|---|---|---|---|",
    ]
    for row in study_audit_df.sort_values("study_id").itertuples():
        lines.append(f"| {row.study_id} | {row.n_records} | {int(row.n_complete)} | "
                     f"{row.pct_audit_trail_complete:.2f}% |")

    lines += [
        "",
        "## Records missing a complete audit trail (remediation list)",
        "",
        f"**{len(missing_df)} records** across the portfolio are missing a complete audit "
        f"trail entry and are flagged for remediation review:",
        "",
        "| Record ID | Study | Type | Modifications | Create entries logged | Update entries logged |",
        "|---|---|---|---|---|---|",
    ]
    for row in missing_df.itertuples():
        lines.append(f"| {row.record_id} | {row.study_id} | {row.record_type} | "
                     f"{row.n_modifications} | {row.n_create_entries} | {row.n_update_entries} |")

    lines += [
        "",
        "## 21 CFR Part 11 compliance documentation",
        "",
        f"**Mean {mean_compliance_pct:.1f}%** of required compliance documentation items "
        f"present across studies; **{n_studies_full_compliance} of {len(compliance_df)} studies** "
        f"have all required items on file (electronic signature policy, access control "
        f"policy, record retention policy, audit trail review procedure, system validation "
        f"documentation).",
        "",
        "| Study | Items present | Items required | % Present |",
        "|---|---|---|---|",
    ]
    for row in compliance_df.sort_values("study_id").itertuples():
        lines.append(f"| {row.study_id} | {row.n_present} | {row.n_required} | "
                     f"{row.pct_compliance_docs_present:.1f}% |")

    lines += [
        "",
        "## Figures",
        "",
        "- `output/figures/audit_trail_completeness_by_study.png`",
        "- `output/figures/missing_audit_trail_by_study.png`",
        "- `output/figures/compliance_documentation_heatmap.png`",
    ]

    with open(os.path.join(OUTPUT_DIR, "governance_report.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    record_df, study_audit_df, compliance_df = load()
    missing_df = missing_audit_records(record_df)

    make_figures(study_audit_df, missing_df, compliance_df)
    write_report(record_df, study_audit_df, compliance_df, missing_df)

    n_complete, n_total, overall_pct = overall_completeness(record_df)
    mean_compliance_pct = compliance_df["pct_compliance_docs_present"].mean()

    print("=" * 60)
    print("CLINICAL TRIAL DATA GOVERNANCE ANALYSIS")
    print("=" * 60)
    print(f"Studies: {record_df['study_id'].nunique()}")
    print(f"Total records: {n_total}")
    print(f"Overall audit trail completeness: {overall_pct:.2f}% ({n_complete}/{n_total})")
    print(f"Records missing complete audit trail: {len(missing_df)}")
    print(f"Mean compliance documentation %: {mean_compliance_pct:.1f}%")
    print(f"Studies with 100% compliance documentation: "
          f"{int((compliance_df['pct_compliance_docs_present'] == 100.0).sum())} of {len(compliance_df)}")
    print("\nWrote output/governance_report.md, output/figures/*.png")


if __name__ == "__main__":
    main()
