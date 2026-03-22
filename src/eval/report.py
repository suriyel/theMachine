"""ReportGenerator — Markdown report for retrieval quality evaluation.

Produces reports with overall scores, per-stage breakdowns, per-language
breakdowns, weak spots, and delta comparison with previous reports.
"""

from __future__ import annotations

import re
from datetime import date

from src.eval.runner import StageMetrics

METRIC_NAMES = ["mrr_at_10", "ndcg_at_10", "recall_at_200", "precision_at_3"]
METRIC_HEADERS = ["MRR@10", "NDCG@10", "Recall@200", "Precision@3"]


class ReportGenerator:
    """Generates Markdown evaluation reports from StageMetrics."""

    def generate(
        self,
        stages: list[StageMetrics],
        prev_report: str | None = None,
    ) -> str:
        """Generate a Markdown evaluation report."""
        if not stages:
            raise ValueError("At least one stage required")

        sections: list[str] = []
        sections.append(self._render_header())
        sections.append(self._render_overall_table(stages))

        for stage in stages:
            sections.append(self._render_stage_detail(stage))

        sections.append(self._render_per_language(stages))
        sections.append(self._render_weak_spots(stages))

        if prev_report is not None:
            prev_metrics = self._parse_previous_report(prev_report)
            if prev_metrics:
                deltas = self._compute_deltas(stages, prev_metrics)
                sections.append(self._render_delta_section(deltas))
            else:
                sections.append(
                    "## Delta Comparison\n\nNo comparable metrics found in previous report."
                )

        return "\n\n".join(sections)

    def _render_header(self) -> str:
        today = date.today().isoformat()
        return (
            f"# Retrieval Quality Evaluation Report\n\n"
            f"**Date**: {today}"
        )

    def _render_overall_table(self, stages: list[StageMetrics]) -> str:
        lines = ["## Overall Scores", ""]
        lines.append(
            f"| Stage | {' | '.join(METRIC_HEADERS)} |"
        )
        lines.append(
            f"|{'|'.join(['-------'] * (len(METRIC_HEADERS) + 1))}|"
        )
        for s in stages:
            vals = [
                self._fmt(getattr(s, m)) for m in METRIC_NAMES
            ]
            lines.append(f"| {s.stage} | {' | '.join(vals)} |")
        return "\n".join(lines)

    def _render_stage_detail(self, stage: StageMetrics) -> str:
        lines = [f"### {stage.stage.title()}", ""]
        if stage.status == "N/A":
            lines.append("Stage not yet implemented — N/A.")
            return "\n".join(lines)

        lines.append(f"- **Status**: {stage.status}")
        lines.append(f"- **Queries evaluated**: {stage.query_count}")
        for metric, header in zip(METRIC_NAMES, METRIC_HEADERS):
            val = getattr(stage, metric)
            lines.append(f"- **{header}**: {self._fmt(val)}")
        return "\n".join(lines)

    def _render_per_language(self, stages: list[StageMetrics]) -> str:
        lines = ["## Per-Language Breakdown", ""]

        # Collect all languages
        all_langs: set[str] = set()
        for s in stages:
            all_langs.update(s.per_language.keys())

        if not all_langs:
            lines.append("No per-language data available.")
            return "\n".join(lines)

        for lang in sorted(all_langs):
            lines.append(f"### {lang.title()}")
            lines.append("")
            lines.append(
                f"| Stage | {' | '.join(METRIC_HEADERS)} |"
            )
            lines.append(
                f"|{'|'.join(['-------'] * (len(METRIC_HEADERS) + 1))}|"
            )
            for s in stages:
                lang_metrics = s.per_language.get(lang)
                if lang_metrics:
                    vals = [
                        self._fmt(lang_metrics.get(m))
                        for m in METRIC_NAMES
                    ]
                else:
                    vals = ["N/A"] * len(METRIC_NAMES)
                lines.append(f"| {s.stage} | {' | '.join(vals)} |")
            lines.append("")
        return "\n".join(lines)

    def _render_weak_spots(self, stages: list[StageMetrics]) -> str:
        lines = ["## Weak Spots", ""]
        weak_found = False

        for s in stages:
            if s.status == "N/A":
                continue
            for metric, header in zip(METRIC_NAMES, METRIC_HEADERS):
                val = getattr(s, metric)
                if val is not None and val < 0.5:
                    lines.append(
                        f"- **{s.stage}** {header}: {self._fmt(val)} (below 0.50 threshold)"
                    )
                    weak_found = True

        if not weak_found:
            lines.append("No weak spots identified.")
        return "\n".join(lines)

    def _render_delta_section(
        self, deltas: dict[str, dict[str, float | None]]
    ) -> str:
        lines = ["## Delta Comparison", ""]
        lines.append(
            f"| Stage | {' | '.join('Δ ' + h for h in METRIC_HEADERS)} |"
        )
        lines.append(
            f"|{'|'.join(['-------'] * (len(METRIC_HEADERS) + 1))}|"
        )

        for stage_name, metric_deltas in deltas.items():
            vals: list[str] = []
            for m in METRIC_NAMES:
                d = metric_deltas.get(m)
                if d is None:
                    vals.append("N/A")
                else:
                    vals.append(f"{d:+.4f}")
            lines.append(f"| {stage_name} | {' | '.join(vals)} |")
        return "\n".join(lines)

    def _parse_previous_report(
        self, report: str
    ) -> dict[str, dict[str, float | None]]:
        """Parse overall scores table from previous Markdown report."""
        result: dict[str, dict[str, float | None]] = {}
        lines = report.split("\n")
        in_table = False

        for line in lines:
            if "| Stage |" in line:
                in_table = True
                continue
            if in_table and line.strip().startswith("|---"):
                continue
            if in_table and line.strip().startswith("|"):
                cols = [c.strip() for c in line.split("|")[1:-1]]
                if len(cols) >= 5:
                    stage = cols[0].lower().strip()
                    result[stage] = {
                        "mrr_at_10": self._parse_float(cols[1]),
                        "ndcg_at_10": self._parse_float(cols[2]),
                        "recall_at_200": self._parse_float(cols[3]),
                        "precision_at_3": self._parse_float(cols[4]),
                    }
            elif in_table:
                in_table = False

        return result

    def _compute_deltas(
        self,
        stages: list[StageMetrics],
        prev_metrics: dict[str, dict[str, float | None]],
    ) -> dict[str, dict[str, float | None]]:
        """Compute signed deltas between current and previous metrics."""
        deltas: dict[str, dict[str, float | None]] = {}
        for s in stages:
            prev = prev_metrics.get(s.stage, {})
            stage_deltas: dict[str, float | None] = {}
            for m in METRIC_NAMES:
                curr_val = getattr(s, m)
                prev_val = prev.get(m)
                if curr_val is not None and prev_val is not None:
                    stage_deltas[m] = curr_val - prev_val
                else:
                    stage_deltas[m] = None
            deltas[s.stage] = stage_deltas
        return deltas

    @staticmethod
    def _fmt(val: float | None) -> str:
        """Format a metric value for display."""
        if val is None:
            return "N/A"
        return f"{val:.4f}"

    @staticmethod
    def _parse_float(s: str) -> float | None:
        """Parse a float from a table cell, returning None for N/A."""
        s = s.strip()
        if s.upper() == "N/A" or not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
