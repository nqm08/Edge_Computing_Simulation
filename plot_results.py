"""
Generate thesis charts from simulation results.
Produces 4 figures: Latency, Throughput, CPU Utilization, Packet Loss
"""

import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "results.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "charts")

ALGORITHMS = ["Round Robin", "Random", "Least Loaded", "Weighted LB"]
SCENARIOS = [1, 2, 3, 4]
SCENARIO_LABELS = ["10 users\n(Low)", "30 users\n(Medium)", "60 users\n(High)", "100 users\n(Stress)"]

COLORS = {
    "Round Robin":   "#4C72B0",
    "Random":        "#DD8452",
    "Least Loaded":  "#55A868",
    "Weighted LB":   "#C44E52",
}
MARKERS = {
    "Round Robin":  "o",
    "Random":       "s",
    "Least Loaded": "^",
    "Weighted LB":  "D",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 12,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "figure.dpi": 150,
})


def load_results() -> dict:
    data = {algo: {sc: {} for sc in SCENARIOS} for algo in ALGORITHMS}
    with open(RESULTS_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            algo = row["algorithm"]
            sc = int(row["scenario"])
            data[algo][sc] = {
                "latency":   float(row["avg_latency_ms"]),
                "throughput": float(row["throughput_mbps"]),
                "cpu":        float(row["avg_cpu_utilization"]) * 100,
                "loss":       float(row["packet_loss_rate"]) * 100,
            }
    return data


def plot_line(data: dict, metric: str, ylabel: str, title: str, filename: str):
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(SCENARIOS))

    for algo in ALGORITHMS:
        values = [data[algo][sc][metric] for sc in SCENARIOS]
        ax.plot(x, values, marker=MARKERS[algo], color=COLORS[algo],
                linewidth=2, markersize=7, label=algo)

    ax.set_xticks(x)
    ax.set_xticklabels(SCENARIO_LABELS)
    ax.set_xlabel("Simulation Scenario")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc="upper left", framealpha=0.9)
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_bar_grouped(data: dict, metric: str, ylabel: str, title: str, filename: str):
    n_algos = len(ALGORITHMS)
    n_sc = len(SCENARIOS)
    x = np.arange(n_sc)
    width = 0.18

    fig, ax = plt.subplots(figsize=(10, 5.5))
    for i, algo in enumerate(ALGORITHMS):
        values = [data[algo][sc][metric] for sc in SCENARIOS]
        offset = (i - n_algos / 2 + 0.5) * width
        bars = ax.bar(x + offset, values, width, label=algo,
                      color=COLORS[algo], edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003 * max(values),
                    f"{val:.1f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(SCENARIO_LABELS)
    ax.set_xlabel("Simulation Scenario")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc="upper left", framealpha=0.9)
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_cpu_heatmap(data: dict):
    matrix = np.array([
        [data[algo][sc]["cpu"] for sc in SCENARIOS]
        for algo in ALGORITHMS
    ])
    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(matrix, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(range(len(SCENARIOS)))
    ax.set_xticklabels(SCENARIO_LABELS)
    ax.set_yticks(range(len(ALGORITHMS)))
    ax.set_yticklabels(ALGORITHMS)
    ax.set_title("CPU Utilization Heatmap (%)")
    plt.colorbar(im, ax=ax, label="CPU Utilization (%)")
    for i in range(len(ALGORITHMS)):
        for j in range(len(SCENARIOS)):
            ax.text(j, i, f"{matrix[i,j]:.1f}%",
                    ha="center", va="center", fontsize=10,
                    color="white" if matrix[i, j] > 60 else "black")
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "cpu_heatmap.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_summary_radar(data: dict):
    # Use scenario 4 (stress) for radar comparison
    metrics = ["latency", "throughput", "cpu", "loss"]
    metric_labels = ["Latency (ms)", "Throughput (Mbps)", "CPU Util. (%)", "Packet Loss (%)"]
    sc = 4

    raw = {algo: [data[algo][sc][m] for m in metrics] for algo in ALGORITHMS}
    # Normalize 0–1, lower is better for latency & loss, higher is better for throughput
    maxvals = [max(raw[a][i] for a in ALGORITHMS) for i in range(4)]
    minvals = [min(raw[a][i] for a in ALGORITHMS) for i in range(4)]

    def normalize(val, mn, mx, invert=False):
        if mx == mn:
            return 0.5
        n = (val - mn) / (mx - mn)
        return 1 - n if invert else n

    normalized = {}
    for algo in ALGORITHMS:
        v = raw[algo]
        normalized[algo] = [
            normalize(v[0], minvals[0], maxvals[0], invert=True),   # latency: lower=better
            normalize(v[1], minvals[1], maxvals[1], invert=False),   # throughput: higher=better
            normalize(v[2], minvals[2], maxvals[2], invert=True),    # cpu: lower=better
            normalize(v[3], minvals[3], maxvals[3], invert=True),    # loss: lower=better
        ]

    angles = np.linspace(0, 2 * np.pi, 4, endpoint=False).tolist()
    angles += angles[:1]
    metric_labels += metric_labels[:1]

    fig, ax = plt.subplots(figsize=(6.5, 6.5), subplot_kw={"polar": True})
    for algo in ALGORITHMS:
        vals = normalized[algo] + normalized[algo][:1]
        ax.plot(angles, vals, color=COLORS[algo], linewidth=2, marker=MARKERS[algo], markersize=6, label=algo)
        ax.fill(angles, vals, color=COLORS[algo], alpha=0.1)

    ax.set_thetagrids(np.degrees(angles[:-1]), metric_labels[:-1])
    ax.set_ylim(0, 1)
    ax.set_title("Algorithm Comparison — Stress Scenario\n(higher = better performance)", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), framealpha=0.9)
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "radar_comparison.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = load_results()

    print("\nGenerating charts...")
    plot_line(data, "latency",    "Average Latency (ms)",       "Average Latency by Scenario",       "latency_line.png")
    plot_line(data, "throughput", "Throughput (Mbps)",           "Throughput by Scenario",             "throughput_line.png")
    plot_line(data, "loss",       "Packet Loss Rate (%)",        "Packet Loss Rate by Scenario",       "packet_loss_line.png")
    plot_bar_grouped(data, "cpu", "CPU Utilization (%)",         "CPU Utilization by Scenario",        "cpu_bar.png")
    plot_cpu_heatmap(data)
    plot_summary_radar(data)
    print(f"\nAll charts saved to: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
