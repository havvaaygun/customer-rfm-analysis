"""RFM scoring and customer segmentation. Writes rfm_table.csv, segment_summary.csv and charts."""

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
REPORTS = os.path.join(ROOT, "reports")
CHARTS = os.path.join(REPORTS, "charts")

SNAPSHOT = pd.Timestamp("2026-01-01")
plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.25,
                     "axes.spines.top": False, "axes.spines.right": False})


def build_rfm():
    df = pd.read_csv(os.path.join(DATA_DIR, "transactions.csv"), parse_dates=["invoice_date"])
    rfm = df.groupby("customer_id").agg(
        recency=("invoice_date", lambda x: (SNAPSHOT - x.max()).days),
        frequency=("invoice_id", "nunique"),
        monetary=("amount", "sum"),
    ).reset_index()

    # quintile scores 1-5, same idea as NTILE(5) in the SQL version.
    # lower recency is better, so its labels are reversed
    rfm["R"] = pd.qcut(rfm["recency"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M"] = pd.qcut(rfm["monetary"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["rfm_score"] = rfm["R"] + rfm["F"] + rfm["M"]
    rfm["rfm_cell"] = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)
    return rfm


def segment(row):
    r = row["R"]
    fm = (row["F"] + row["M"]) / 2
    if r >= 4 and fm >= 4:
        return "Champions"
    if r >= 3 and fm >= 3:
        return "Loyal Customers"
    if r >= 4 and fm <= 2:
        return "New / Promising"
    if r >= 3 and fm <= 2:
        return "Potential Loyalists"
    if r <= 2 and fm >= 4:
        return "At Risk"
    if r <= 2 and fm >= 3:
        return "Needs Attention"
    if r <= 2 and fm <= 2:
        return "Hibernating / Lost"
    return "Others"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, name), dpi=130)
    plt.close(fig)


def charts(rfm, summary):
    s = summary.sort_values("customers")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(s["segment"], s["customers"], color="#2E5EAA")
    ax.set_title("Müşteri Sayısına Göre Segmentler", fontweight="bold")
    ax.set_xlabel("Müşteri sayısı")
    save(fig, "01_segment_sizes.png")

    s = summary.sort_values("revenue")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(s["segment"], s["revenue"], color="#E4572E")
    ax.set_title("Segmentlerin Gelir Katkısı", fontweight="bold")
    ax.set_xlabel("Toplam gelir (TL)")
    save(fig, "02_segment_revenue.png")

    fig, ax = plt.subplots(figsize=(7.5, 6))
    sizes = rfm["monetary"] / rfm["monetary"].max() * 300 + 10
    sc = ax.scatter(rfm["recency"], rfm["frequency"], s=sizes, alpha=0.35,
                    c=rfm["rfm_score"], cmap="viridis")
    ax.set_xlabel("Recency (gün - düşük daha iyi)")
    ax.set_ylabel("Frequency (sipariş sayısı)")
    ax.set_title("RFM Dağılımı (renk = RFM skoru, boyut = harcama)", fontweight="bold")
    fig.colorbar(sc, label="RFM skoru")
    save(fig, "03_rfm_scatter.png")


def main():
    os.makedirs(CHARTS, exist_ok=True)
    rfm = build_rfm()
    rfm["segment"] = rfm.apply(segment, axis=1)

    summary = rfm.groupby("segment").agg(
        customers=("customer_id", "count"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        revenue=("monetary", "sum"),
    ).reset_index()
    summary["customer_share_pct"] = summary["customers"] / summary["customers"].sum() * 100
    summary["revenue_share_pct"] = summary["revenue"] / summary["revenue"].sum() * 100
    summary = summary.round(1).sort_values("revenue", ascending=False)

    rfm.round(2).to_csv(os.path.join(REPORTS, "rfm_table.csv"), index=False)
    summary.to_csv(os.path.join(REPORTS, "segment_summary.csv"), index=False)
    charts(rfm, summary)

    print(summary[["segment", "customers", "customer_share_pct", "avg_recency",
                   "avg_frequency", "avg_monetary", "revenue_share_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
