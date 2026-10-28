"""
KPI Aggregation & Business Performance Analytics Engine
Computes executive-level e-commerce metrics, period-over-period comparisons,
and multi-dimensional revenue breakdowns using Pandas and NumPy.
"""

from collections import defaultdict
from datetime import datetime
import numpy as np

# Dual-mode support: Try importing pandas, fallback to robust NumPy/Python engine if WDAC restricts pandas C-libs
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    PANDAS_AVAILABLE = False


def calculate_kpis(records, start_date=None, end_date=None, region_filter="All", category_filter="All", status_filter="All"):
    """
    Main aggregation pipeline. Applies filters and calculates:
    - Consolidated Executive KPIs (Gross, Discounts, Returns, Net Sales, Order Count, AOV, Growth)
    - Monthly Revenue Trends with MoM Growth %
    - Product Category Performance Breakdown
    - Regional Performance Breakdown
    - Category x Region Pivot Matrix
    - Cancelled orders & operational risk metrics
    """
    if not records:
        return _empty_kpi_payload()

    # Step 1: Filter raw records
    filtered = []
    for r in records:
        # Date filter
        o_date = r["order_date"]
        if start_date and o_date < start_date:
            continue
        if end_date and o_date > end_date:
            continue
        # Region filter
        if region_filter != "All" and r["region"] != region_filter:
            continue
        # Category filter
        if category_filter != "All" and r["category"] != category_filter:
            continue
        # Status filter
        if status_filter != "All" and r["order_status"] != status_filter:
            continue
        filtered.append(r)

    if not filtered:
        return _empty_kpi_payload()

    # Step 2: Management Business Logic & Exclusions
    # Consistent Treatment:
    # - Cancelled orders are strictly EXCLUDED from Gross Sales, Discounts, Returns, Net Sales, and Net Order Count.
    # - Cancelled orders are tracked separately to evaluate Cancellation Rate & lost bookings.
    total_orders_placed_ids = set()
    cancelled_order_ids = set()
    valid_order_ids = set()

    # High-level accumulator variables
    total_gross_sales = 0.0
    total_discounts = 0.0
    total_returns = 0.0
    total_units_sold = 0
    cancelled_potential_sales = 0.0

    # Grouping accumulators
    monthly_data = defaultdict(lambda: {
        "gross_sales": 0.0,
        "discounts": 0.0,
        "returns": 0.0,
        "net_sales": 0.0,
        "valid_orders": set(),
        "total_orders": set(),
        "cancelled_orders": set(),
        "units": 0
    })

    category_data = defaultdict(lambda: {
        "gross_sales": 0.0,
        "discounts": 0.0,
        "returns": 0.0,
        "net_sales": 0.0,
        "valid_orders": set(),
        "units": 0
    })

    region_data = defaultdict(lambda: {
        "gross_sales": 0.0,
        "discounts": 0.0,
        "returns": 0.0,
        "net_sales": 0.0,
        "valid_orders": set(),
        "units": 0
    })

    cat_region_matrix = defaultdict(lambda: defaultdict(float))

    for row in filtered:
        oid = row["order_id"]
        status = row["order_status"]
        ym = row["order_date"][:7]  # YYYY-MM
        cat = row["category"]
        reg = row["region"]
        qty = int(row["quantity"])
        price = float(row["unit_price"])
        disc = float(row.get("discount_optional") or 0.0)
        ret = float(row.get("return_amount_optional") or 0.0)

        total_orders_placed_ids.add(oid)
        monthly_data[ym]["total_orders"].add(oid)

        line_gross = qty * price

        if status == "Cancelled":
            cancelled_order_ids.add(oid)
            cancelled_potential_sales += line_gross
            monthly_data[ym]["cancelled_orders"].add(oid)
            # Skip business revenue recognition for cancelled orders
            continue

        # Valid order processing
        valid_order_ids.add(oid)
        total_gross_sales += line_gross
        total_discounts += disc
        total_returns += ret
        total_units_sold += qty

        line_net = line_gross - disc - ret

        # Aggregate monthly
        m = monthly_data[ym]
        m["gross_sales"] += line_gross
        m["discounts"] += disc
        m["returns"] += ret
        m["net_sales"] += line_net
        m["valid_orders"].add(oid)
        m["units"] += qty

        # Aggregate category
        c = category_data[cat]
        c["gross_sales"] += line_gross
        c["discounts"] += disc
        c["returns"] += ret
        c["net_sales"] += line_net
        c["valid_orders"].add(oid)
        c["units"] += qty

        # Aggregate region
        rg = region_data[reg]
        rg["gross_sales"] += line_gross
        rg["discounts"] += disc
        rg["returns"] += ret
        rg["net_sales"] += line_net
        rg["valid_orders"].add(oid)
        rg["units"] += qty

        # Cross matrix
        cat_region_matrix[cat][reg] += line_net

    # Step 3: Compute Overall Key Performance Indicators (KPIs)
    total_net_sales = total_gross_sales - total_discounts - total_returns
    valid_order_count = len(valid_order_ids)
    total_placed_count = len(total_orders_placed_ids)
    cancelled_count = len(cancelled_order_ids)

    aov_net = (total_net_sales / valid_order_count) if valid_order_count > 0 else 0.0
    aov_gross = (total_gross_sales / valid_order_count) if valid_order_count > 0 else 0.0
    avg_basket_size = (total_units_sold / valid_order_count) if valid_order_count > 0 else 0.0
    cancellation_rate = ((cancelled_count / total_placed_count) * 100.0) if total_placed_count > 0 else 0.0
    return_rate = ((total_returns / total_gross_sales) * 100.0) if total_gross_sales > 0 else 0.0
    discount_rate = ((total_discounts / total_gross_sales) * 100.0) if total_gross_sales > 0 else 0.0

    # Step 4: Monthly Trend Aggregation & Period Comparisons (MoM Growth %)
    sorted_months = sorted(monthly_data.keys())
    monthly_trend_list = []
    net_sales_series = []
    gross_sales_series = []
    order_count_series = []

    for ym in sorted_months:
        item = monthly_data[ym]
        m_valid_orders = len(item["valid_orders"])
        m_cancelled_orders = len(item["cancelled_orders"])
        m_total_orders = len(item["total_orders"])
        m_gross = item["gross_sales"]
        m_disc = item["discounts"]
        m_ret = item["returns"]
        m_net = item["net_sales"]
        m_aov = (m_net / m_valid_orders) if m_valid_orders > 0 else 0.0

        net_sales_series.append(m_net)
        gross_sales_series.append(m_gross)
        order_count_series.append(m_valid_orders)

        monthly_trend_list.append({
            "month": ym,
            "gross_sales": round(m_gross, 2),
            "discounts": round(m_disc, 2),
            "returns": round(m_ret, 2),
            "net_sales": round(m_net, 2),
            "order_count": m_valid_orders,
            "total_orders": m_total_orders,
            "cancelled_orders": m_cancelled_orders,
            "aov": round(m_aov, 2),
            "units_sold": item["units"],
            "mom_net_growth_pct": 0.0,
            "mom_order_growth_pct": 0.0
        })

    # Vectorized NumPy Percentage-Change Calculations for MoM Growth
    if len(net_sales_series) > 1:
        net_arr = np.array(net_sales_series, dtype=np.float64)
        order_arr = np.array(order_count_series, dtype=np.float64)

        # NumPy diff and safe percentage change: ((current - prev) / prev) * 100
        net_growth = np.zeros(len(net_arr), dtype=np.float64)
        with np.errstate(divide='ignore', invalid='ignore'):
            growth_calc = np.diff(net_arr) / net_arr[:-1] * 100.0
            growth_calc = np.nan_to_num(growth_calc, nan=0.0, posinf=0.0, neginf=0.0)
            net_growth[1:] = growth_calc

        order_growth = np.zeros(len(order_arr), dtype=np.float64)
        with np.errstate(divide='ignore', invalid='ignore'):
            ord_calc = np.diff(order_arr) / order_arr[:-1] * 100.0
            ord_calc = np.nan_to_num(ord_calc, nan=0.0, posinf=0.0, neginf=0.0)
            order_growth[1:] = ord_calc

        for idx, entry in enumerate(monthly_trend_list):
            entry["mom_net_growth_pct"] = round(float(net_growth[idx]), 2)
            entry["mom_order_growth_pct"] = round(float(order_growth[idx]), 2)

    # Latest MoM Growth benchmark (comparing latest completed month vs previous month)
    latest_mom_growth = 0.0
    latest_order_growth = 0.0
    if len(monthly_trend_list) >= 2:
        latest_mom_growth = monthly_trend_list[-1]["mom_net_growth_pct"]
        latest_order_growth = monthly_trend_list[-1]["mom_order_growth_pct"]

    # Step 5: Product Category Performance
    categories_list = []
    for cat, val in category_data.items():
        c_net = val["net_sales"]
        c_gross = val["gross_sales"]
        c_orders = len(val["valid_orders"])
        c_returns = val["returns"]
        c_share = ((c_net / total_net_sales) * 100.0) if total_net_sales > 0 else 0.0
        c_ret_rate = ((c_returns / c_gross) * 100.0) if c_gross > 0 else 0.0
        c_aov = (c_net / c_orders) if c_orders > 0 else 0.0

        categories_list.append({
            "category": cat,
            "gross_sales": round(c_gross, 2),
            "discounts": round(val["discounts"], 2),
            "returns": round(c_returns, 2),
            "net_sales": round(c_net, 2),
            "order_count": c_orders,
            "units_sold": val["units"],
            "share_pct": round(c_share, 2),
            "return_rate_pct": round(c_ret_rate, 2),
            "aov": round(c_aov, 2)
        })
    categories_list.sort(key=lambda x: x["net_sales"], reverse=True)

    # Step 6: Regional Performance
    regions_list = []
    for reg, val in region_data.items():
        r_net = val["net_sales"]
        r_gross = val["gross_sales"]
        r_orders = len(val["valid_orders"])
        r_share = ((r_net / total_net_sales) * 100.0) if total_net_sales > 0 else 0.0
        r_aov = (r_net / r_orders) if r_orders > 0 else 0.0

        regions_list.append({
            "region": reg,
            "gross_sales": round(r_gross, 2),
            "discounts": round(val["discounts"], 2),
            "returns": round(val["returns"], 2),
            "net_sales": round(r_net, 2),
            "order_count": r_orders,
            "units_sold": val["units"],
            "share_pct": round(r_share, 2),
            "aov": round(r_aov, 2)
        })
    regions_list.sort(key=lambda x: x["net_sales"], reverse=True)

    # Step 7: Category x Region Matrix (formatted table)
    matrix_regions = sorted(list({r["region"] for r in regions_list}))
    matrix_rows = []
    for cat_item in categories_list:
        cat_name = cat_item["category"]
        row_dict = {"category": cat_name, "total": cat_item["net_sales"]}
        for r_name in matrix_regions:
            row_dict[r_name] = round(cat_region_matrix[cat_name].get(r_name, 0.0), 2)
        matrix_rows.append(row_dict)

    # Step 8: Comparative Period Diagnostics (Latest vs Previous Month)
    latest_month_data = None
    previous_month_data = None
    month_comparison = {
        "has_comparison": False,
        "latest_month": None,
        "previous_month": None,
        "diff_net_sales": 0.0,
        "diff_gross_sales": 0.0,
        "diff_order_count": 0,
        "growth_net_pct": 0.0,
        "growth_order_pct": 0.0
    }

    if len(monthly_trend_list) >= 2:
        latest = monthly_trend_list[-1]
        prev = monthly_trend_list[-2]
        latest_month_data = latest
        previous_month_data = prev
        diff_net = latest["net_sales"] - prev["net_sales"]
        diff_gross = latest["gross_sales"] - prev["gross_sales"]
        diff_ord = latest["order_count"] - prev["order_count"]

        month_comparison = {
            "has_comparison": True,
            "latest_month": latest["month"],
            "previous_month": prev["month"],
            "latest_net_sales": latest["net_sales"],
            "previous_net_sales": prev["net_sales"],
            "diff_net_sales": round(diff_net, 2),
            "diff_gross_sales": round(diff_gross, 2),
            "diff_order_count": diff_ord,
            "growth_net_pct": latest["mom_net_growth_pct"],
            "growth_order_pct": latest["mom_order_growth_pct"]
        }
    elif len(monthly_trend_list) == 1:
        latest_month_data = monthly_trend_list[0]
        month_comparison = {
            "has_comparison": False,
            "latest_month": latest_month_data["month"],
            "previous_month": None,
            "latest_net_sales": latest_month_data["net_sales"],
            "previous_net_sales": 0.0,
            "diff_net_sales": 0.0,
            "diff_gross_sales": 0.0,
            "diff_order_count": 0,
            "growth_net_pct": 0.0,
            "growth_order_pct": 0.0
        }

    # Top performing highlights
    top_category = categories_list[0] if categories_list else None
    top_region = regions_list[0] if regions_list else None

    # Consolidated KPI Summary Object
    kpi_summary = {
        "total_gross_sales": round(total_gross_sales, 2),
        "total_discounts": round(total_discounts, 2),
        "total_returns": round(total_returns, 2),
        "total_net_sales": round(total_net_sales, 2),
        "order_count": valid_order_count,
        "total_orders_placed": total_placed_count,
        "cancelled_orders": cancelled_count,
        "cancelled_potential_sales": round(cancelled_potential_sales, 2),
        "aov_net": round(aov_net, 2),
        "aov_gross": round(aov_gross, 2),
        "avg_basket_size": round(avg_basket_size, 2),
        "cancellation_rate": round(cancellation_rate, 2),
        "return_rate": round(return_rate, 2),
        "discount_rate": round(discount_rate, 2),
        "latest_mom_growth": round(latest_mom_growth, 2),
        "latest_order_growth": round(latest_order_growth, 2),
        "total_units_sold": total_units_sold,
        "currency_symbol": "$",
        "currency_code": "USD",
        "reporting_period": f"{sorted_months[0]} to {sorted_months[-1]}" if sorted_months else "All Data"
    }

    return {
        "kpis": kpi_summary,
        "monthly_trends": monthly_trend_list,
        "categories": categories_list,
        "regions": regions_list,
        "matrix_regions": matrix_regions,
        "category_region_matrix": matrix_rows,
        "month_comparison": month_comparison,
        "top_category": top_category,
        "top_region": top_region
    }


def _empty_kpi_payload():
    """Fallback when no records match filter criteria."""
    return {
        "kpis": {
            "total_gross_sales": 0.0,
            "total_discounts": 0.0,
            "total_returns": 0.0,
            "total_net_sales": 0.0,
            "order_count": 0,
            "total_orders_placed": 0,
            "cancelled_orders": 0,
            "cancelled_potential_sales": 0.0,
            "aov_net": 0.0,
            "aov_gross": 0.0,
            "avg_basket_size": 0.0,
            "cancellation_rate": 0.0,
            "return_rate": 0.0,
            "discount_rate": 0.0,
            "latest_mom_growth": 0.0,
            "latest_order_growth": 0.0,
            "total_units_sold": 0,
            "currency_symbol": "$",
            "currency_code": "USD",
            "reporting_period": "No Data Selected"
        },
        "monthly_trends": [],
        "categories": [],
        "regions": [],
        "matrix_regions": [],
        "category_region_matrix": [],
        "month_comparison": {
            "has_comparison": False,
            "latest_month": None,
            "previous_month": None,
            "diff_net_sales": 0.0,
            "diff_gross_sales": 0.0,
            "diff_order_count": 0,
            "growth_net_pct": 0.0,
            "growth_order_pct": 0.0
        },
        "top_category": None,
        "top_region": None
    }
