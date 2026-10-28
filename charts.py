"""
Visualization Engine for E-Commerce BI Dashboard.
Generates executive-grade charts using Matplotlib (headless Agg backend).
Renders high-resolution Base64-encoded PNG images for web display and reports.
"""

import io
import base64
import matplotlib
matplotlib.use('Agg')  # Headless backend for web server
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# Executive color palette
COLORS = {
    "primary": "#4f46e5",    # Indigo
    "secondary": "#06b6d4",  # Cyan
    "accent": "#10b981",     # Emerald
    "warning": "#f59e0b",    # Amber
    "danger": "#ef4444",     # Rose/Red
    "purple": "#8b5cf6",     # Violet
    "dark": "#1e293b",       # Slate 800
    "muted": "#64748b",      # Slate 500
    "bg_card": "#ffffff",
    "grid": "#e2e8f0"
}

PALETTE = ["#4f46e5", "#06b6d4", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#14b8a6"]


def _fig_to_base64(fig):
    """Encodes a matplotlib figure to base64 PNG string and closes the figure."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=130, facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)
    return img_b64


def generate_revenue_trend_chart(monthly_trends):
    """
    Dual-axis chart:
    - Primary axis: Monthly Gross Sales vs Net Sales (Bars / Fill)
    - Secondary axis: MoM Net Sales Growth Rate % (Dotted/Marker line)
    """
    if not monthly_trends:
        return None

    months = [m["month"] for m in monthly_trends]
    gross = [m["gross_sales"] / 1000.0 for m in monthly_trends]  # in $k
    net = [m["net_sales"] / 1000.0 for m in monthly_trends]      # in $k
    growth = [m["mom_net_growth_pct"] for m in monthly_trends]

    x = np.arange(len(months))
    width = 0.38

    fig, ax1 = plt.subplots(figsize=(11, 4.8), facecolor='#ffffff')
    ax1.set_facecolor('#ffffff')

    # Bars for Gross and Net Sales
    rects1 = ax1.bar(x - width/2, gross, width, label='Gross Sales ($k)', color='#c7d2fe', edgecolor='#818cf8', alpha=0.9)
    rects2 = ax1.bar(x + width/2, net, width, label='Net Sales ($k)', color='#4f46e5', edgecolor='#3730a3', alpha=0.95)

    ax1.set_ylabel('Revenue ($ in Thousands)', color='#1e293b', fontsize=11, fontweight='600')
    ax1.tick_params(axis='y', labelcolor='#1e293b')
    ax1.set_xticks(x)
    # Display every 2nd or 3rd label if many months
    step = 1 if len(months) <= 12 else (2 if len(months) <= 24 else 3)
    ax1.set_xticklabels([m if i % step == 0 else '' for i, m in enumerate(months)], rotation=45, ha='right', fontsize=9)
    ax1.grid(True, linestyle='--', alpha=0.4, color='#cbd5e1', axis='y')

    # Secondary axis for Growth %
    ax2 = ax1.twinx()
    line = ax2.plot(x, growth, color='#10b981', linewidth=2.4, marker='o', markersize=5, label='MoM Net Growth %')
    ax2.axhline(0, color='#94a3b8', linestyle=':', linewidth=1)
    ax2.set_ylabel('MoM Growth Rate (%)', color='#047857', fontsize=11, fontweight='600')
    ax2.tick_params(axis='y', labelcolor='#047857')

    # Combined Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', frameon=True, facecolor='#f8fafc', edgecolor='#e2e8f0', fontsize=9)

    plt.title('Monthly Store Revenue Trends & MoM Growth Velocity', fontsize=13, fontweight='bold', color='#0f172a', pad=15)
    return _fig_to_base64(fig)


def generate_category_comparison_chart(categories):
    """
    Horizontal Bar Chart comparing Net Sales by Category with Gross Sales overlay.
    """
    if not categories:
        return None

    cats = [c["category"] for c in reversed(categories)]
    net = [c["net_sales"] / 1000.0 for c in reversed(categories)]
    gross = [c["gross_sales"] / 1000.0 for c in reversed(categories)]
    shares = [c["share_pct"] for c in reversed(categories)]

    y = np.arange(len(cats))
    height = 0.42

    fig, ax = plt.subplots(figsize=(9, 4.8), facecolor='#ffffff')
    ax.set_facecolor('#ffffff')

    ax.barh(y + height/2, gross, height, label='Gross Sales ($k)', color='#e0e7ff', edgecolor='#a5b4fc')
    bars = ax.barh(y - height/2, net, height, label='Net Sales ($k)', color='#4f46e5', edgecolor='#3730a3')

    # Data value labels on bars
    for idx, (bar, share, n_val) in enumerate(zip(bars, shares, net)):
        ax.text(n_val + max(gross)*0.015, bar.get_y() + bar.get_height()/2, f"${n_val:,.1f}k ({share:.1f}%)",
                va='center', ha='left', fontsize=8.5, fontweight='bold', color='#1e293b')

    ax.set_yticks(y)
    ax.set_yticklabels(cats, fontsize=9.5, fontweight='500', color='#1e293b')
    ax.set_xlabel('Sales ($ in Thousands)', fontsize=10, fontweight='600', color='#1e293b')
    ax.set_xlim(0, max(gross) * 1.25)
    ax.grid(True, linestyle='--', alpha=0.4, color='#cbd5e1', axis='x')
    ax.legend(loc='lower right', frameon=True, facecolor='#f8fafc', edgecolor='#e2e8f0', fontsize=9)

    plt.title('Product Category Revenue Comparison (Gross vs Net)', fontsize=12, fontweight='bold', color='#0f172a', pad=12)
    return _fig_to_base64(fig)


def generate_regional_distribution_chart(regions):
    """
    Donut / Ring chart displaying regional revenue share.
    """
    if not regions:
        return None

    names = [r["region"] for r in regions]
    net_sales = [r["net_sales"] for r in regions]

    fig, ax = plt.subplots(figsize=(6.5, 4.8), facecolor='#ffffff')
    ax.set_facecolor('#ffffff')

    wedges, texts, autotexts = ax.pie(
        net_sales,
        labels=names,
        autopct='%1.1f%%',
        startangle=140,
        colors=PALETTE[:len(regions)],
        pctdistance=0.78,
        wedgeprops=dict(width=0.42, edgecolor='#ffffff', linewidth=2)
    )

    for text in texts:
        text.set_color('#1e293b')
        text.set_fontsize(9.5)
        text.set_fontweight('500')

    for autotext in autotexts:
        autotext.set_color('#ffffff')
        autotext.set_fontsize(8.5)
        autotext.set_fontweight('bold')

    plt.title('Regional Net Revenue Share', fontsize=12, fontweight='bold', color='#0f172a', pad=12)
    return _fig_to_base64(fig)


def generate_consolidated_executive_figure(kpi_data):
    """
    Produces a 2x2 multi-panel Executive BI Management Report in a single high-res canvas.
    Ideal for executive PDF generation, presentation embeds, and print-ready downloads.
    """
    monthly = kpi_data.get("monthly_trends", [])
    categories = kpi_data.get("categories", [])
    regions = kpi_data.get("regions", [])
    kpis = kpi_data.get("kpis", {})

    if not monthly or not categories:
        return None

    fig = plt.figure(figsize=(15, 10.5), facecolor='#f8fafc')

    # Header Title Banner
    fig.suptitle('Executive Business Intelligence Performance Report', fontsize=18, fontweight='bold', color='#0f172a', y=0.98)

    # Subtitle with KPI highlights
    subtitle = (
        f"Net Sales: ${kpis.get('total_net_sales', 0):,.2f}  |  "
        f"Gross Sales: ${kpis.get('total_gross_sales', 0):,.2f}  |  "
        f"Orders: {kpis.get('order_count', 0):,}  |  "
        f"Net AOV: ${kpis.get('aov_net', 0):,.2f}  |  "
        f"Latest MoM Growth: {kpis.get('latest_mom_growth', 0):+.1f}%"
    )
    plt.figtext(0.5, 0.945, subtitle, ha='center', fontsize=11, color='#475569', fontweight='500')

    # Panel 1: Revenue Trends (Top-Left)
    ax1 = fig.add_subplot(2, 2, 1)
    months = [m["month"] for m in monthly]
    net_k = [m["net_sales"] / 1000.0 for m in monthly]
    gross_k = [m["gross_sales"] / 1000.0 for m in monthly]
    ax1.plot(months, gross_k, label='Gross ($k)', color='#818cf8', linestyle='--', linewidth=1.8, marker='o', markersize=3)
    ax1.plot(months, net_k, label='Net Sales ($k)', color='#4f46e5', linewidth=2.5, marker='s', markersize=4)
    ax1.set_title('Revenue Trajectory ($ in Thousands)', fontsize=11, fontweight='bold', color='#1e293b')
    ax1.set_ylabel('Revenue ($k)', fontsize=9, color='#475569')
    step = max(1, len(months) // 8)
    ax1.set_xticks(range(len(months)))
    ax1.set_xticklabels([m if i % step == 0 else '' for i, m in enumerate(months)], rotation=45, ha='right', fontsize=8)
    ax1.grid(True, linestyle='--', alpha=0.4, color='#cbd5e1')
    ax1.legend(loc='upper left', fontsize=8.5, frameon=True)

    # Panel 2: Category Net Sales (Top-Right)
    ax2 = fig.add_subplot(2, 2, 2)
    top_cats = sorted(categories, key=lambda x: x["net_sales"], reverse=True)[:6]
    c_names = [c["category"] for c in reversed(top_cats)]
    c_net = [c["net_sales"] / 1000.0 for c in reversed(top_cats)]
    bars = ax2.barh(c_names, c_net, color='#06b6d4', edgecolor='#0891b2')
    for bar, val in zip(bars, c_net):
        ax2.text(val + max(c_net)*0.015, bar.get_y() + bar.get_height()/2, f"${val:,.1f}k",
                 va='center', ha='left', fontsize=8, fontweight='bold', color='#1e293b')
    ax2.set_xlim(0, max(c_net) * 1.25)
    ax2.set_title('Top Product Categories by Net Revenue ($k)', fontsize=11, fontweight='bold', color='#1e293b')
    ax2.grid(True, linestyle='--', alpha=0.4, color='#cbd5e1', axis='x')

    # Panel 3: Regional Share (Bottom-Left)
    ax3 = fig.add_subplot(2, 2, 3)
    r_names = [r["region"] for r in regions]
    r_net = [r["net_sales"] for r in regions]
    ax3.pie(r_net, labels=r_names, autopct='%1.1f%%', colors=PALETTE[:len(regions)], startangle=140,
            textprops={'fontsize': 8.5}, wedgeprops=dict(edgecolor='#ffffff', linewidth=1.5))
    ax3.set_title('Regional Net Sales Distribution', fontsize=11, fontweight='bold', color='#1e293b')

    # Panel 4: Top-Line Erosion: Gross vs Discounts vs Returns vs Net (Bottom-Right)
    ax4 = fig.add_subplot(2, 2, 4)
    components = ['Gross Sales', 'Promotional\nDiscounts', 'Customer\nReturns', 'Retained\nNet Sales']
    values = [
        kpis.get('total_gross_sales', 0) / 1000.0,
        -kpis.get('total_discounts', 0) / 1000.0,
        -kpis.get('total_returns', 0) / 1000.0,
        kpis.get('total_net_sales', 0) / 1000.0
    ]
    bar_colors = ['#4f46e5', '#f59e0b', '#ef4444', '#10b981']
    comp_bars = ax4.bar(components, values, color=bar_colors, edgecolor='#334155', width=0.55)
    for bar, val in zip(comp_bars, values):
        y_pos = val + (max(values)*0.02 if val >= 0 else -max(values)*0.05)
        ax4.text(bar.get_x() + bar.get_width()/2, y_pos, f"${abs(val):,.1f}k",
                 ha='center', fontsize=8.5, fontweight='bold', color='#1e293b')
    ax4.axhline(0, color='#64748b', linewidth=1)
    ax4.set_title('Revenue Waterline: Gross to Net Sales Realization ($k)', fontsize=11, fontweight='bold', color='#1e293b')
    ax4.grid(True, linestyle='--', alpha=0.4, color='#cbd5e1', axis='y')

    plt.tight_layout(rect=[0, 0.02, 1, 0.93])
    return _fig_to_base64(fig)
