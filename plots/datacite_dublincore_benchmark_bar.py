"""Generate a poster-style bar chart for the DataCite to Dublin Core benchmark."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "plots" / "poster_datacite_dublincore_benchmark_bar.png"
BENCHMARK = ROOT / "exports" / "benchmark" / "datacite_dc_oai_awi_benchmark.json"


def main() -> None:
    benchmark = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    aggregate = benchmark["aggregate"]
    n_cases = aggregate["cases"]
    metrics = [
        ("Field coverage", aggregate["avg_field_coverage"] * 100),
        ("Value overlap", aggregate["avg_value_overlap"] * 100),
    ]

    palette = {
        "dark_blue": "#002864",
        "light_blue": "#14c8ff",
        "ast": "#50c8aa",
        "health": "#D23264",
        "matter": "#f0781e",
        "blue_highlight": "#cdeefb",
    }
    background = "#ffffff"
    muted = "#4b5563"

    labels = [metric[0] for metric in metrics]
    values = [metric[1] for metric in metrics]
    gaps = [100 - value for value in values]
    y_positions = list(range(len(metrics)))

    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=400)
    fig.patch.set_facecolor(background)
    ax.set_facecolor(background)

    bar_colors = [palette["health"], palette["matter"]]
    ax.barh(
        y_positions,
        values,
        color=bar_colors,
        height=0.42,
        edgecolor=background,
        linewidth=2.5,
        zorder=3,
    )
    ax.barh(
        y_positions,
        gaps,
        left=values,
        color=palette["blue_highlight"],
        height=0.42,
        edgecolor=background,
        linewidth=2.5,
        alpha=0.75,
        zorder=2,
    )

    for index, value in enumerate(values):
        label_color = "white"
        ax.text(
            value - 2.2,
            index,
            f"{value:.1f}%",
            ha="right",
            va="center",
            fontsize=20,
            fontweight="heavy",
            color=label_color,
            zorder=4,
        )

    ax.set_yticks(
        y_positions, labels, fontsize=14, fontweight="bold", color=palette["dark_blue"]
    )
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25", "50", "75", "100%"], fontsize=11, color=muted)
    ax.tick_params(axis="y", length=0, pad=14)
    ax.tick_params(axis="x", length=0, pad=8)
    ax.grid(axis="x", color="#e5e7eb", linewidth=1.1, zorder=1)

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_title(
        "DataCite to Dublin Core Benchmark",
        fontsize=22,
        fontweight="heavy",
        color=palette["dark_blue"],
        pad=34,
    )
    ax.text(
        0.5,
        1.01,
        f"Live OAI-PMH benchmark against reference Dublin Core records (n={n_cases})",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=11.5,
        fontweight="bold",
        color=muted,
    )
    plt.subplots_adjust(top=0.74, bottom=0.16, left=0.24, right=0.96)
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
