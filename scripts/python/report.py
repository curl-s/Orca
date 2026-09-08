"""Render a DiffReport as the terminal report format requested for the MVP."""

from __future__ import annotations

from .models import DiffReport


def _hex(addr: int) -> str:
    return f"0x{addr:x}"


def render_report(report: DiffReport, show_identical: bool = False) -> str:
    lines: list[str] = []
    lines.append(f"{report.old_path} -> {report.new_path}")
    lines.append(
        f"Overall similarity: {report.overall_similarity * 100:.1f}%  "
        f"(confidence: {report.overall_confidence * 100:.1f}%)"
    )
    lines.append(
        f"Matched: {len(report.matched)} "
        f"({report.identical_count} identical, {len(report.modified)} modified)  "
        f"Added: {len(report.added)}  Removed: {len(report.removed)}"
    )
    lines.append("")

    modified = report.modified
    if modified:
        lines.append("Modified:")
        for m in sorted(modified, key=lambda e: e.similarity):
            display_name = m.name_new if m.name_new == m.name_old else f"{m.name_old} -> {m.name_new}"
            lines.append(display_name)
            lines.append(f"{_hex(m.addr_old)} -> {_hex(m.addr_new)}")
            lines.append(f"similarity: {m.similarity * 100:.0f}%")
            lines.append("")

    if report.added:
        lines.append("Added:")
        for f in sorted(report.added, key=lambda e: e.addr):
            lines.append(f"{f.name}  ({_hex(f.addr)})")
        lines.append("")

    if report.removed:
        lines.append("Removed:")
        for f in sorted(report.removed, key=lambda e: e.addr):
            lines.append(f"{f.name}  ({_hex(f.addr)})")
        lines.append("")

    if show_identical:
        identical = [m for m in report.matched if m.is_identical]
        if identical:
            lines.append("Identical (unchanged) matches:")
            for m in sorted(identical, key=lambda e: e.addr_old):
                lines.append(f"{m.name_old}  {_hex(m.addr_old)} -> {_hex(m.addr_new)}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
