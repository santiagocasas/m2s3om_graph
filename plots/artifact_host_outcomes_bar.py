"""Generate a bar chart for fetched and failed RDAMSC artifact hosts."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "exports" / "pipeline" / "latest" / "rdamsc_artifacts.csv"
OUTPUT = ROOT / "plots" / "poster_artifact_host_outcomes_bar.png"


def main() -> None:
    fetched: Counter[str] = Counter()
    failed: Counter[str] = Counter()
    with ARTIFACTS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            host = row.get("host") or "(unknown)"
            status = row.get("check_status") or "(unknown)"
            if status == "fetched":
                fetched[host] += 1
            elif status == "fetch_error":
                failed[host] += 1

    totals = fetched + failed
    hosts = [host for host, _count in totals.most_common(12)]
    fetched_values = [fetched[host] for host in hosts]
    failed_values = [failed[host] for host in hosts]
    y_positions = list(range(len(hosts)))

    palette = {
        "dark_blue": "#002864",
        "fair_data_commons": "#8cd600",
        "information": "#a0235a",
    }
    background = "#ffffff"
    muted = "#4b5563"
    grid = "#e5e7eb"

    fig, ax = plt.subplots(figsize=(9.2, 6.2), dpi=400)
    fig.patch.set_facecolor(background)
    ax.set_facecolor(background)

    ax.barh(
        y_positions,
        fetched_values,
        color=palette["fair_data_commons"],
        height=0.36,
        label="Fetched",
        edgecolor=background,
        linewidth=2.0,
        zorder=3,
    )
    ax.barh(
        [position + 0.36 for position in y_positions],
        failed_values,
        color=palette["information"],
        height=0.36,
        label="Fetch failed",
        edgecolor=background,
        linewidth=2.0,
        zorder=3,
    )

    for index, (ok_count, fail_count) in enumerate(zip(fetched_values, failed_values, strict=True)):
        if ok_count:
            ax.text(
                ok_count + 0.12,
                index,
                str(ok_count),
                va="center",
                ha="left",
                fontsize=10.5,
                fontweight="bold",
                color=palette["dark_blue"],
            )
        if fail_count:
            ax.text(
                fail_count + 0.12,
                index + 0.36,
                str(fail_count),
                va="center",
                ha="left",
                fontsize=10.5,
                fontweight="bold",
                color=palette["dark_blue"],
            )

    ax.set_yticks([position + 0.18 for position in y_positions], hosts)
    ax.invert_yaxis()
    ax.set_xlim(0, max(fetched_values + failed_values) + 1.6)
    ax.set_xlabel("artifact URLs", fontsize=12, fontweight="bold", color=muted)
    ax.tick_params(axis="x", labelsize=10.5, length=0, colors=muted)
    ax.tick_params(axis="y", labelsize=10.5, length=0, colors=palette["dark_blue"])
    ax.grid(axis="x", color=grid, linewidth=1.1, zorder=1)

    for label in ax.get_yticklabels():
        label.set_fontweight("bold")
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.legend(
        loc="lower right",
        frameon=False,
        fontsize=11,
        labelcolor=palette["dark_blue"],
    )
    ax.set_title(
        "Artifact URL Hosts",
        fontsize=22,
        fontweight="heavy",
        color=palette["dark_blue"],
        pad=34,
    )
    ax.text(
        0.5,
        1.01,
        "Fetched vs failed artifact URLs in the frozen RDAMSC pipeline snapshot",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=11.5,
        fontweight="bold",
        color=muted,
    )

    plt.subplots_adjust(top=0.82, bottom=0.12, left=0.34, right=0.96)
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
