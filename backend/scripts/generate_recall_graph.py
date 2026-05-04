# 役割: Recall@5 改善推移グラフを画像として出力するスクリプト
# 実行: docker compose exec backend python scripts/generate_recall_graph.py
# 出力: /app/docs/images/recall_progress.png (ホスト: backend/docs/images/recall_progress.png)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import japanize_matplotlib  # noqa: F401  日本語フォント自動設定
import numpy as np

steps = [
    "ベースライン\n(ベクトル検索のみ)",
    "クエリ拡張\n(失敗・不採用)",
    "ハイブリッド検索\n(BM25+Vector+RRF)",
    "BM25\nN-gram化",
    "文書追加\n+eval修正",
    "用語集削除\n(ノイズ除去)",
]
recall = [0.33, 0.08, 0.58, 0.58, 0.92, 0.92]
counts = ["4/12", "1/12", "7/12", "7/12", "11/12", "11/12"]

fig, ax = plt.subplots(figsize=(11, 5))
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

x = np.arange(len(steps))

ax.axhline(y=0.80, color="#E24B4A", linewidth=1.2, linestyle="--", alpha=0.8, zorder=1)
ax.text(5.35, 0.81, "目標値 0.80", color="#E24B4A", fontsize=9, va="bottom")

for i in range(len(recall) - 1):
    color = "#E24B4A" if i == 0 else "#378ADD"
    ls = "--" if i == 0 else "-"
    ax.plot([x[i], x[i+1]], [recall[i], recall[i+1]],
            color=color, linewidth=2, linestyle=ls, zorder=2)

ax.fill_between(x[1:], recall[1:], alpha=0.08, color="#378ADD", zorder=1)

point_colors = ["#378ADD", "#E24B4A", "#378ADD", "#378ADD", "#1D9E75", "#1D9E75"]
for i, (xi, yi, pc) in enumerate(zip(x, recall, point_colors)):
    marker = "v" if i == 1 else "o"
    ax.scatter(xi, yi, color=pc, s=80, zorder=5, marker=marker)
    ax.annotate(f"{yi:.2f}\n({counts[i]})",
                xy=(xi, yi), xytext=(0, 12),
                textcoords="offset points",
                ha="center", fontsize=9, color=pc, fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(steps, fontsize=9)
ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
ax.set_ylim(0, 1.15)
ax.set_ylabel("Recall@5", fontsize=10)
ax.set_title("RAG-for-Lab  Recall@5 改善推移", fontsize=13, fontweight="bold", pad=14)
ax.grid(axis="y", linestyle="--", alpha=0.3)
ax.spines[["top", "right"]].set_visible(False)

legend_handles = [
    mpatches.Patch(color="#378ADD", label="改善ステップ"),
    mpatches.Patch(color="#E24B4A", label="失敗・不採用"),
    mpatches.Patch(color="#1D9E75", label="目標値達成"),
]
ax.legend(handles=legend_handles, fontsize=9, loc="lower right")

plt.tight_layout()
plt.savefig("/app/docs/images/recall_progress.png", dpi=150, bbox_inches="tight")
print("saved: docs/images/recall_progress.png")
