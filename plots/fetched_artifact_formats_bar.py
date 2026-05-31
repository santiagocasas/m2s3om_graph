"""Generate a poster-style bar chart for fetched RDAMSC artifact formats."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "plots" / "poster_fetched_artifact_formats_bar.png"
STATS = ROOT / "exports" / "pipeline" / "latest" / "rdamsc_stats_summary.json"


def main() -> None:
    stats = json.loads(STATS.read_text(encoding="utf-8"))
    fetched = stats["artifact_checks"]["extension_fetched"]
    formats = [".xsl", ".html", ".pdf", ".zip"]
    values = [fetched.get(format_name, 0) for format_name in formats]
    total_fetched = stats["artifact_checks"]["status_counts"].get("fetched", sum(values))

    palette = {
        "dark_blue": "#002864",
        "ast": "#50c8aa",
        "health": "#D23264",
        "matter": "#f0781e",
        "fair_data_commons": "#8cd600",
        "information": "#a0235a",
    }
    background = "#ffffff"
    muted = "#4b5563"
    grid = "#e5e7eb"

    fig, ax = plt.subplots(figsize=(8.2, 5.0), dpi=400)
    fig.patch.set_facecolor(background)
    ax.set_facecolor(background)

    colors = [
        palette["dark_blue"],
        palette["health"],
        palette["matter"],
        palette["fair_data_commons"],
    ]
    bars = ax.bar(
        formats,
        values,
        color=colors,
        width=0.58,
        edgecolor=background,
        linewidth=2.5,
        zorder=3,
    )

    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.25,
            str(value),
            ha="center",
            va="bottom",
            fontsize=20,
            fontweight="heavy",
            color=palette["dark_blue"],
        )

    ax.set_ylim(0, max(values) + 2.1)
    ax.set_yticks(range(0, max(values) + 3, 2))
    ax.set_ylabel("fetched artifacts", fontsize=12, fontweight="bold", color=muted)
    ax.tick_params(axis="x", labelsize=15, length=0, pad=10, colors=palette["dark_blue"])
    ax.tick_params(axis="y", labelsize=11, length=0, colors=muted)
    for label in ax.get_xticklabels():
        label.set_fontweight("bold")
    ax.grid(axis="y", color=grid, linewidth=1.1, zorder=1)

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_title(
        "Fetched Artifact Formats",
        fontsize=22,
        fontweight="heavy",
        color=palette["dark_blue"],
        pad=34,
    )
    ax.text(
        0.5,
        1.01,
        f"Top RDAMSC artifact formats in the frozen pipeline snapshot ({total_fetched} fetched artifacts)",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=11.5,
        fontweight="bold",
        color=muted,
    )
    plt.subplots_adjust(top=0.76, bottom=0.17, left=0.12, right=0.96)
    fig.savefig(
        OUTPUT,
        dpi=400,
        facecolor=fig.get_facecolor(),
        bbox_inches="tight",
        pad_inches=0.20,
    )
    plt.close(fig)
    print(OUTPUT)


if __name__ == "__main__":
    main()
