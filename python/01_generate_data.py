"""Creates a synthetic transaction log for 2,000 customers over two years."""

import os
import numpy as np
import pandas as pd

RNG = np.random.default_rng(7)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

N_CUSTOMERS = 2000
SNAPSHOT = pd.Timestamp("2026-01-01")
HISTORY_DAYS = 730

# customer type: (share, avg orders, days since last order, avg spend)
CUSTOMER_TYPES = {
    "champion": (0.12, 24, 15, 180),
    "loyal": (0.22, 12, 45, 120),
    "potential": (0.20, 6, 70, 90),
    "new": (0.12, 2, 20, 70),
    "at_risk": (0.18, 8, 230, 110),
    "hibernating": (0.16, 3, 400, 60),
}


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    rows = []
    cust_id = 1000
    for ctype, (share, avg_orders, recency_days, avg_spend) in CUSTOMER_TYPES.items():
        for _ in range(int(N_CUSTOMERS * share)):
            cust_id += 1
            n_orders = max(1, int(RNG.poisson(avg_orders)))
            last_gap = max(1, int(RNG.normal(recency_days, recency_days * 0.3)))
            last_purchase = SNAPSHOT - pd.Timedelta(days=min(last_gap, HISTORY_DAYS))
            for g in np.sort(RNG.integers(0, HISTORY_DAYS, size=n_orders)):
                d = min(SNAPSHOT - pd.Timedelta(days=int(g)), last_purchase)
                amount = round(max(10, RNG.normal(avg_spend, avg_spend * 0.4)), 2)
                rows.append({
                    "customer_id": f"CUST-{cust_id:05d}",
                    "invoice_date": d.date().isoformat(),
                    "invoice_id": f"INV-{RNG.integers(100000, 999999)}",
                    "amount": amount,
                    "segment_truth": ctype,
                })

    df = pd.DataFrame(rows).sort_values(["customer_id", "invoice_date"]).reset_index(drop=True)
    df.to_csv(os.path.join(DATA_DIR, "transactions.csv"), index=False)
    print(f"{len(df):,} transactions, {df['customer_id'].nunique():,} customers")


if __name__ == "__main__":
    main()
