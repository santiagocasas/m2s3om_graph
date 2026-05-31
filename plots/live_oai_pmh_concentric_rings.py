from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
PLOTS = Path(__file__).resolve().parent

palette = {
    "dark_blue": "#002864",
    "ast": "#50c8aa",
    "health": "#D23264",
    "matter": "#f0781e",
    "fair_data_commons": "#8cd600",
    "information": "#a0235a",
}
background = "#ffffff"
empty_ring = "#e5e7eb"
muted = "#4b5563"

outer_label = "Records processed"
outer_n = 1000

metrics = [
    ("Completed", 100.0, palette["fair_data_commons"]),
    ("Field coverage", 30.9, palette["health"]),
    ("Value overlap", 16.7, palette["matter"]),
    ("Semantic loss rate", 26.4, palette["information"]),
]

fig, ax = plt.subplots(figsize=(9, 9))
fig.patch.set_facecolor(background)
ax.set_facecolor(background)
ax.set_aspect("equal")

outer_radius = 1.25
outer_width = 0.16
inner_radii = [1.02, 0.79, 0.56, 0.33]
inner_width = 0.16

outer_wedges, _ = ax.pie(
    [100, 0.0001],
    radius=outer_radius,
    startangle=90,
    counterclock=False,
    colors=[palette["dark_blue"], empty_ring],
    wedgeprops=dict(width=outer_width, edgecolor=background, linewidth=3.0),
)

legend_handles = []
legend_labels = []

for (label, value, color), radius in zip(metrics, inner_radii):
    wedges, _ = ax.pie(
        [value, 100 - value],
        radius=radius,
        startangle=90,
        counterclock=False,
        colors=[color, empty_ring],
        wedgeprops=dict(width=inner_width, edgecolor=background, linewidth=3.0),
    )
    legend_handles.append(Patch(facecolor=wedges[0].get_facecolor(), edgecolor="none"))
    legend_labels.append(f"{label}: {value:.1f}%")

legend_handles.insert(0, Patch(facecolor=outer_wedges[0].get_facecolor(), edgecolor="none"))
legend_labels.insert(0, f"{outer_label}: n = {outer_n:,}")

ax.text(
    0,
    0.08,
    "n = 1,000",
    ha="center",
    va="center",
    fontsize=24,
    fontweight="bold",
    color=palette["dark_blue"],
)
ax.text(
    0,
    -0.10,
    "live OAI-PMH\nrecords",
    ha="center",
    va="center",
    fontsize=12,
    fontweight="bold",
    color=muted,
)

ax.set_title(
    "Live OAI-PMH Stress Test\nConcentric benchmark rings",
    fontsize=18,
    fontweight="bold",
    color=palette["dark_blue"],
    pad=24,
)

ax.legend(
    legend_handles,
    legend_labels,
    loc="center left",
    bbox_to_anchor=(1.02, 0.5),
    frameon=False,
    title="Legend",
    labelcolor=palette["dark_blue"],
)

ax.set_axis_off()

PLOTS.mkdir(exist_ok=True)
fig.savefig(
    PLOTS / "live_oai_pmh_concentric_rings.png",
    dpi=400,
    bbox_inches="tight",
    facecolor=background,
)
fig.savefig(
    PLOTS / "live_oai_pmh_concentric_rings.svg",
    bbox_inches="tight",
    facecolor=background,
)
plt.show()
