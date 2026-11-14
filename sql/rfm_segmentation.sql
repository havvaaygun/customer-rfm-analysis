-- =====================================================================
-- Customer Segmentation & RFM Analysis (PostgreSQL)
-- =====================================================================
-- Recency / Frequency / Monetary scoring with NTILE(5), then a business
-- segment per customer. Mirrors python/02_rfm_analysis.py.
-- =====================================================================

DROP TABLE IF EXISTS transactions;
CREATE TABLE transactions (
    customer_id    TEXT,
    invoice_date   DATE,
    invoice_id     TEXT,
    amount         NUMERIC(10,2),
    segment_truth  TEXT
);
-- \copy transactions FROM 'data/transactions.csv' CSV HEADER;

-- Analysis snapshot ("today")
-- Change this date if you regenerate the data.
-- SET snapshot = DATE '2026-01-01';

-- ---------- 1. Base RFM metrics -------------------------------------
WITH rfm_base AS (
    SELECT
        customer_id,
        DATE '2026-01-01' - MAX(invoice_date)        AS recency,
        COUNT(DISTINCT invoice_id)                   AS frequency,
        SUM(amount)                                  AS monetary
    FROM transactions
    GROUP BY customer_id
),
-- ---------- 2. 1-5 scores with NTILE --------------------------------
rfm_scored AS (
    SELECT
        customer_id, recency, frequency, monetary,
        -- recency: lower is better -> invert the ntile
        6 - NTILE(5) OVER (ORDER BY recency ASC)          AS r,
        NTILE(5) OVER (ORDER BY frequency ASC)            AS f,
        NTILE(5) OVER (ORDER BY monetary ASC)             AS m
    FROM rfm_base
),
-- ---------- 3. Business segments ------------------------------------
rfm_segmented AS (
    SELECT
        *,
        (r + f + m) AS rfm_score,
        CASE
            WHEN r >= 4 AND (f + m) / 2.0 >= 4 THEN 'Champions'
            WHEN r >= 3 AND (f + m) / 2.0 >= 3 THEN 'Loyal Customers'
            WHEN r >= 4 AND (f + m) / 2.0 <= 2 THEN 'New / Promising'
            WHEN r >= 3 AND (f + m) / 2.0 <= 2 THEN 'Potential Loyalists'
            WHEN r <= 2 AND (f + m) / 2.0 >= 4 THEN 'At Risk'
            WHEN r <= 2 AND (f + m) / 2.0 >= 3 THEN 'Needs Attention'
            WHEN r <= 2 AND (f + m) / 2.0 <= 2 THEN 'Hibernating / Lost'
            ELSE 'Others'
        END AS segment
    FROM rfm_scored
)
-- ---------- 4. Per-customer table -----------------------------------
SELECT * FROM rfm_segmented
ORDER BY rfm_score DESC;


-- ---------- 5. Segment summary (size + revenue contribution) --------
WITH rfm_base AS (
    SELECT customer_id,
           DATE '2026-01-01' - MAX(invoice_date) AS recency,
           COUNT(DISTINCT invoice_id)            AS frequency,
           SUM(amount)                           AS monetary
    FROM transactions GROUP BY customer_id
),
rfm_scored AS (
    SELECT customer_id, recency, frequency, monetary,
           6 - NTILE(5) OVER (ORDER BY recency ASC) AS r,
           NTILE(5) OVER (ORDER BY frequency ASC)   AS f,
           NTILE(5) OVER (ORDER BY monetary ASC)    AS m
    FROM rfm_base
),
seg AS (
    SELECT monetary,
        CASE
            WHEN r >= 4 AND (f + m) / 2.0 >= 4 THEN 'Champions'
            WHEN r >= 3 AND (f + m) / 2.0 >= 3 THEN 'Loyal Customers'
            WHEN r >= 4 AND (f + m) / 2.0 <= 2 THEN 'New / Promising'
            WHEN r >= 3 AND (f + m) / 2.0 <= 2 THEN 'Potential Loyalists'
            WHEN r <= 2 AND (f + m) / 2.0 >= 4 THEN 'At Risk'
            WHEN r <= 2 AND (f + m) / 2.0 >= 3 THEN 'Needs Attention'
            WHEN r <= 2 AND (f + m) / 2.0 <= 2 THEN 'Hibernating / Lost'
            ELSE 'Others'
        END AS segment
    FROM rfm_scored
)
SELECT
    segment,
    COUNT(*)                                             AS customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)   AS customer_share_pct,
    ROUND(SUM(monetary), 2)                              AS revenue,
    ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS revenue_share_pct
FROM seg
GROUP BY segment
ORDER BY revenue DESC;
