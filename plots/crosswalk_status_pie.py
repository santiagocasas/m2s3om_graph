"""Generate a poster-style pie chart for RDAMSC crosswalk processing status."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "plots" / "poster_crosswalk_status_pie.png"
STATS = ROOT / "exports" / "pipeline" / "latest" / "rdamsc_stats_summary.json"


def main() -> None:
    stats = json.loads(STATS.read_text(encoding="utf-8"))
    counts = stats["status_counts"]

    labels = [
        "SSSOM ready",
        "Document unreachable",
        "Fetched, no rules extracted",
    ]
    values = [
        counts.get("ready", 0),
        counts.get("failed_unreachable", 0),
        counts.get("failed_parse", 0),
    ]
    total = sum(values)

    colors = [
        "#002864",  # hmc_dark_blue
        "#14c8ff",  # hmc_light_blue
        "#f0781e",  # hmc_matter
    ]
    ink = "#002864"
    muted = "#4b5563"
    background = "#ffffff"

    fig, ax = plt.subplots(figsize=(7.2, 7.2), dpi=400)
    fig.patch.set_facecolor(background)
    ax.set_facecolor(background)

    wedges, _texts, autotexts = ax.pie(
        values,
        startangle=92,
        counterclock=False,
        colors=colors,
        autopct=lambda pct: f"{pct:.1f}%\n({round(pct * total / 100):.0f})",
        pctdistance=0.74,
        wedgeprops={"width": 0.50, "edgecolor": background, "linewidth": 4.5},
        textprops={
            "color": "white",
            "fontsize": 10.8,
            "fontweight": "bold",
            "ha": "center",
            "va": "center",
            "linespacing": 1.15,
        },
    )
    autotexts[1].set_color(ink)

    ax.text(
        0,
        0.09,
        str(total),
        ha="center",
        va="center",
        fontsize=54,
        fontweight="heavy",
        color=ink,
    )
    ax.text(
        0,
        -0.15,
        "RDAMSC\ncrosswalks",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=muted,
        linespacing=1.05,
    )
    ax.set_title(
        "Crosswalk Processing Outcomes",
        fontsize=22,
        fontweight="heavy",
        color=ink,
        pad=20,
    )

    legend_labels = [
        f"{label}: {value}/{total}" for label, value in zip(labels, values, strict=True)
    ]
    legend = ax.legend(
        wedges,
        legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.10),
        ncol=1,
        frameon=False,
        fontsize=12,
        handlelength=1.2,
        handletextpad=0.7,
    )
    for text in legend.get_texts():
        text.set_color(ink)
        text.set_fontweight("bold")

    ax.text(
        0.5,
        -0.18,
        "Frozen pipeline snapshot · SSSOM extraction readiness",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=10.5,
        color=muted,
    )

    ax.set_aspect("equal")
    plt.subplots_adjust(top=0.88, bottom=0.20, left=0.06, right=0.94)
    fig.savefig(
        OUTPUT,
        dpi=400,
        facecolor=fig.get_facecolor(),
        bbox_inches="tight",
        pad_inches=0.18,
    )
    plt.close(fig)
    print(OUTPUT)


if __name__ == "__main__":
    main()
