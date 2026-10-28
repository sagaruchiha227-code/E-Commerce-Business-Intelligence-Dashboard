"""
KPI Definitions and Business Rules Engine
Centralized reference for all business intelligence formulas, management rationale,
inclusion/exclusion criteria, and accounting governance standards.
"""

KPI_DEFINITIONS = [
    {
        "id": "gross_sales",
        "number": 1,
        "name": "Gross Sales",
        "short_name": "Gross Sales",
        "category": "Revenue & Topline",
        "formula": r"\sum (\text{quantity} \times \text{unit\_price})",
        "plain_formula": "Sum of (Quantity * Unit Price) for eligible orders before discounts and returns",
        "description": "Total gross customer purchasing demand and top-line transaction value across all fulfilled and active orders before promotional discounts and customer merchandise returns.",
        "inclusions": "Orders with status 'Completed', 'Shipped', 'Delivered', and 'Pending'.",
        "exclusions": "Strictly excludes orders where order_status = 'Cancelled', as cancelled transactions generate zero commercial cash flow.",
        "management_utility": "Serves as the primary indicator of consumer demand scale, market reach, and gross checkout velocity.",
        "format": "currency"
    },
    {
        "id": "net_sales",
        "number": 2,
        "name": "Net Sales",
        "short_name": "Net Sales",
        "category": "Revenue & Topline",
        "formula": r"\text{Gross Sales} - \text{Discounts} - \text{Returns}",
        "plain_formula": "Gross Sales - Total Discounts - Total Returns",
        "description": "The true realized economic revenue recognized and retained by the enterprise from commercial operations to fund cost of goods (COGS), operational overhead, and profit margins.",
        "inclusions": "Gross sales minus promotional discounts minus post-purchase merchandise refunds across all valid orders.",
        "exclusions": "Strictly excludes cancelled orders. Reflects actual retained revenue.",
        "management_utility": "The primary North Star metric for store financial health, operational viability, and sustainable growth.",
        "format": "currency"
    },
    {
        "id": "order_count",
        "number": 3,
        "name": "Order Count",
        "short_name": "Order Count",
        "category": "Volume & Scale",
        "formula": r"\text{Count}(\text{Distinct Valid } \text{order\_id})",
        "plain_formula": "Number of distinct eligible orders, excluding cancelled orders",
        "description": "Aggregate volume of distinct customer orders successfully submitted and moving through fulfillment. An order containing 5 items is accurately counted as 1 distinct order.",
        "inclusions": "Distinct order identifiers with status Completed, Shipped, Delivered, or Pending.",
        "exclusions": "Orders with order_status = 'Cancelled' are omitted from valid order volume.",
        "management_utility": "Baseline volume metric for fulfillment logistics, operational capacity, and shipping throughput.",
        "format": "integer"
    },
    {
        "id": "aov",
        "number": 4,
        "name": "Average Order Value (AOV)",
        "short_name": "Net AOV",
        "category": "Order Economics",
        "formula": r"\frac{\text{Net Sales}}{\text{Valid Order Count}}",
        "plain_formula": "Net Sales / Number of Eligible Orders",
        "description": "Average net realized revenue generated per completed customer transaction. Reflects consumer spending power and bundling efficiency.",
        "inclusions": "Calculated strictly on net realized sales and distinct valid non-cancelled orders.",
        "exclusions": "Cancelled orders are removed from both numerator and denominator.",
        "management_utility": "Core driver of Customer Lifetime Value (LTV) and advertising spend ceilings (maximum allowable CAC).",
        "format": "currency"
    },
    {
        "id": "growth_rate",
        "number": 5,
        "name": "Revenue Growth",
        "short_name": "Revenue Growth %",
        "category": "Trends & Velocity",
        "formula": r"\left(\frac{\text{Revenue}_t - \text{Revenue}_{t-1}}{\text{Revenue}_{t-1}}\right) \times 100\%",
        "plain_formula": "((Current Period Revenue - Previous Period Revenue) / Previous Period Revenue) * 100",
        "description": "Percentage velocity change comparing the current period's net revenue against the immediately preceding identical period (Month-over-Month MoM).",
        "inclusions": "Sequential matching time intervals.",
        "exclusions": "If previous period revenue is zero or unavailable, growth rate is recorded as 0.0% (N/A) to prevent division by zero.",
        "management_utility": "Measures business acceleration, campaign uplift, and seasonal retail cyclicality.",
        "format": "percent"
    },
    {
        "id": "category_revenue",
        "number": 6,
        "name": "Category Revenue",
        "short_name": "Category Revenue",
        "category": "Product Economics",
        "formula": r"\sum_{i \in \text{Category}} \text{Net Sales}_i",
        "plain_formula": "Net sales aggregated by product category",
        "description": "Total net revenue attributed to specific merchandise categories (e.g. Electronics, Apparel, Home & Kitchen), ranked by financial contribution.",
        "inclusions": "All valid line items belonging to the respective product category.",
        "exclusions": "Items associated with cancelled orders.",
        "management_utility": "Informs inventory procurement, category margin optimization, and merchandising shelf space.",
        "format": "currency"
    },
    {
        "id": "regional_revenue",
        "number": 7,
        "name": "Regional Revenue",
        "short_name": "Regional Revenue",
        "category": "Geographic Performance",
        "formula": r"\sum_{o \in \text{Region}} \text{Net Sales}_o",
        "plain_formula": "Net sales aggregated by geographic region",
        "description": "Total net revenue generated across distinct geographic territories (e.g. North America, Europe, Asia-Pacific) with percentage contribution.",
        "inclusions": "All valid orders originating from the respective geographical region.",
        "exclusions": "Cancelled orders originating from that region.",
        "management_utility": "Guides regional logistics infrastructure, marketing localization, and regional expansion strategy.",
        "format": "currency"
    }
]

# Governance & Technical Implementation Standards
GOVERNANCE_RULES = [
    {
        "topic": "Exclusion of Cancelled Orders",
        "icon": "fa-solid fa-ban",
        "color": "danger",
        "rule": "Strict Exclusion from Revenue & Order Metrics",
        "details": "Orders where order_status = 'Cancelled' are identified at ingestion. They are strictly excluded from Gross Sales, Net Sales, Order Count, Discounts, Returns, and AOV calculations. They are isolated in an operational risk metric ('Cancellation Rate') to evaluate lost commercial potential without corrupting recognized revenue."
    },
    {
        "topic": "Handling of Discounts and Returns",
        "icon": "fa-solid fa-tags",
        "color": "warning",
        "rule": "Systematic Top-Line Deduction",
        "details": "Discounts (promotions, vouchers, markdown concessions) and Customer Returns (post-delivery refunds) are tracked on an item-by-item basis. In Net Sales calculation, both are deducted from Gross Sales: Net Sales = Gross Sales - Discounts - Returns. Discounts on cancelled orders are never applied."
    },
    {
        "topic": "Treatment of Missing or Null Discount & Return Values",
        "icon": "fa-solid fa-circle-question",
        "color": "info",
        "rule": "Default Zero Imputation (COALESCE)",
        "details": "When discount_optional or return_amount_optional are NULL, missing, or empty in the database, the analytics engine automatically defaults them to 0.00 using float(row.get('field') or 0.0). Calculations never fail or produce NaN due to missing optional adjustments."
    },
    {
        "topic": "Duplicate Records and Data Hygiene",
        "icon": "fa-solid fa-shield-halved",
        "color": "primary",
        "rule": "Unique Relational Primary Keys",
        "details": "The database schema enforces PRIMARY KEY constraints on product_id, order_id, and item_id. Unique constraints prevent duplicate insertions. Order items maintain foreign key relationships with ON DELETE CASCADE integrity."
    },
    {
        "topic": "Multi-Product Orders & Distinct Order Counts",
        "icon": "fa-solid fa-cart-shopping",
        "color": "success",
        "rule": "Distinct Order Set Aggregation",
        "details": "Orders frequently contain multiple product line items. To prevent double-counting orders in the aggregation engine, order counts are accumulated into a Python Set (valid_order_ids.add(oid)). The resulting metric is len(valid_order_ids), guaranteeing each order is counted exactly once regardless of how many items it contains."
    },
    {
        "topic": "Zero-Revenue & Edge Case Handling in Period Comparisons",
        "icon": "fa-solid fa-calculator",
        "color": "secondary",
        "rule": "Vectorized NumPy Division Safety",
        "details": "Period-over-period growth is computed using NumPy: growth = (current - prev) / prev * 100. When the previous period has zero revenue, no prior data, or identical dates, np.errstate(divide='ignore', invalid='ignore') suppresses errors, and np.nan_to_num converts division by zero into a clean 0.0% (N/A)."
    },
    {
        "topic": "Assumptions, Boundaries & Exclusions",
        "icon": "fa-solid fa-triangle-exclamation",
        "color": "dark",
        "rule": "Macro Aggregation Scope",
        "details": "This system focuses exclusively on aggregated management-level business performance. In accordance with project boundaries, no individual customer identity, PII, or customer segmentation analysis is stored or computed. Tax, freight, and third-party payment processing fees are treated as downstream COGS outside the top-line gross/net sales scope."
    }
]


def get_all_kpi_definitions():
    """Return list of core KPI definitions."""
    return KPI_DEFINITIONS


def get_governance_rules():
    """Return list of governance and technical handling rules."""
    return GOVERNANCE_RULES
