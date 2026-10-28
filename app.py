"""
Flask Web Application for E-Commerce Business Intelligence Dashboard.
Features:
- Professional SaaS Landing Page
- Secure Authentication (Registration, Login, Password Hashing, Session Management)
- Protected Executive Dashboard (Topline KPIs, Reporting Period, Currency, Period Comparisons)
- Protected Sales Analytics (Monthly Revenue Trajectory, Category Economics, Regional Breakdown)
- Dedicated KPI Documentation & Accounting Governance
- Database Switcher & Migration (SQLite / MySQL)
- Matplotlib & Chart.js Visualizations
"""

import os
import csv
import io
import re
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

from database import (
    CURRENT_CONFIG,
    init_db,
    seed_data,
    seed_default_user,
    fetch_raw_data,
    test_mysql_connection,
    migrate_sqlite_to_mysql,
    create_user,
    get_user_by_email_or_username,
    get_user_by_id,
    REGIONS,
    PRODUCT_CATALOG
)
from kpi_definitions import get_all_kpi_definitions, get_governance_rules
from kpi_engine import calculate_kpis
import charts

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "omnistore-bi-secure-session-key-2026")

ALL_CATEGORIES = sorted(list({p[1] for p in PRODUCT_CATALOG}))
ALL_REGIONS = REGIONS


def login_required(f):
    """Decorator ensuring that only authenticated users can access management routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access the executive dashboard and analytics.", "warning")
            return redirect(url_for("login", next=request.full_path if request.query_string else request.path))
        return f(*args, **kwargs)
    return decorated_function


def _get_filtered_data():
    """Extracts filter query parameters and computes aggregated KPI payload."""
    year = request.args.get("year", "All")
    category = request.args.get("category", "All")
    region = request.args.get("region", "All")
    status = request.args.get("status", "All")

    start_date = None
    end_date = None
    if year != "All":
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

    records = fetch_raw_data()
    kpi_result = calculate_kpis(
        records,
        start_date=start_date,
        end_date=end_date,
        region_filter=region,
        category_filter=category,
        status_filter=status
    )
    return kpi_result, year, category, region, status


@app.context_processor
def inject_global_context():
    """Provides common user state, active DB info, and dimensions to all templates."""
    current_user = None
    if "user_id" in session:
        current_user = {
            "id": session.get("user_id"),
            "name": session.get("user_name"),
            "email": session.get("user_email"),
            "username": session.get("user_username"),
            "role": session.get("user_role", "Executive")
        }
    return {
        "current_user": current_user,
        "is_authenticated": "user_id" in session,
        "current_db_type": CURRENT_CONFIG["db_type"],
        "mysql_config": CURRENT_CONFIG,
        "all_categories": ALL_CATEGORIES,
        "all_regions": ALL_REGIONS
    }


# ========================================================
# Public Routes: Landing Page, Documentation & Auth
# ========================================================

@app.route("/")
def index():
    """Public Landing Page presenting project overview, features, and dashboard preview."""
    records = fetch_raw_data()
    preview_kpi = calculate_kpis(records)

    # Lightweight Matplotlib preview chart for landing page
    trend_preview_b64 = charts.generate_revenue_trend_chart(preview_kpi["monthly_trends"][-12:])

    return render_template(
        "landing.html",
        active_page="landing",
        kpis=preview_kpi["kpis"],
        top_category=preview_kpi["top_category"],
        top_region=preview_kpi["top_region"],
        trend_preview_b64=trend_preview_b64
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    """User authentication with email/username and password."""
    if "user_id" in session:
        return redirect(url_for("dashboard_view"))

    next_url = request.args.get("next") or request.form.get("next") or url_for("dashboard_view")

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        if not identifier or not password:
            flash("Please enter both email/username and password.", "danger")
            return render_template("login.html", active_page="login", next_url=next_url, identifier=identifier)

        user = get_user_by_email_or_username(identifier)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email/username or password. Please try again.", "danger")
            return render_template("login.html", active_page="login", next_url=next_url, identifier=identifier)

        # Successful login: set session
        session["user_id"] = user["user_id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["user_username"] = user["username"]
        session["user_role"] = user.get("role", "Executive")

        flash(f"Welcome back, {user['name']}! Authenticated successfully.", "success")
        return redirect(next_url)

    return render_template("login.html", active_page="login", next_url=next_url)


@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration with full validation and secure password hashing."""
    if "user_id" in session:
        return redirect(url_for("dashboard_view"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "Executive")

        # Field validations
        if not name or not email or not username or not password or not confirm_password:
            flash("All registration fields are required.", "danger")
            return render_template("register.html", active_page="register", name=name, email=email, username=username)

        # Email regex format validation
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, email):
            flash("Please provide a valid email address.", "danger")
            return render_template("register.html", active_page="register", name=name, email=email, username=username)

        # Password match & length validation
        if password != confirm_password:
            flash("Passwords do not match. Please re-enter your password.", "danger")
            return render_template("register.html", active_page="register", name=name, email=email, username=username)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html", active_page="register", name=name, email=email, username=username)

        # Create user with hashed password
        password_hash = generate_password_hash(password)
        success, res = create_user(name, email, username, password_hash, role)

        if not success:
            flash(res, "danger")
            return render_template("register.html", active_page="register", name=name, email=email, username=username)

        # Auto-login upon successful registration
        user_id = res
        session["user_id"] = user_id
        session["user_name"] = name
        session["user_email"] = email
        session["user_username"] = username
        session["user_role"] = role

        flash(f"Account registered successfully! Welcome to OmniStore BI, {name}.", "success")
        return redirect(url_for("dashboard_view"))

    return render_template("register.html", active_page="register")


@app.route("/logout")
def logout():
    """Terminates session and logs user out."""
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("login"))


@app.route("/documentation")
def documentation_view():
    """KPI Documentation and Accounting Governance reference page."""
    defs = get_all_kpi_definitions()
    gov_rules = get_governance_rules()
    return render_template(
        "documentation.html",
        active_page="documentation",
        kpi_list=defs,
        governance_rules=gov_rules
    )


# ========================================================
# Protected Management Routes (Executive Dashboard & Analytics)
# ========================================================

@app.route("/dashboard")
@login_required
def dashboard_view():
    """Executive KPI Dashboard with Topline Metrics & Previous Period Comparisons."""
    kpi_data, year, category, region, status = _get_filtered_data()

    # Generate Matplotlib chart visuals
    trend_chart_b64 = charts.generate_revenue_trend_chart(kpi_data["monthly_trends"])
    category_chart_b64 = charts.generate_category_comparison_chart(kpi_data["categories"])
    region_chart_b64 = charts.generate_regional_distribution_chart(kpi_data["regions"])

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        kpis=kpi_data["kpis"],
        monthly_trends=kpi_data["monthly_trends"],
        categories=kpi_data["categories"],
        regions=kpi_data["regions"],
        month_comparison=kpi_data["month_comparison"],
        selected_year=year,
        selected_category=category,
        selected_region=region,
        selected_status=status,
        trend_chart_b64=trend_chart_b64,
        category_chart_b64=category_chart_b64,
        region_chart_b64=region_chart_b64
    )


@app.route("/analytics")
@login_required
def analytics_view():
    """Sales Analytics Page: Monthly Revenue, Category Economics, and Regional Breakdown."""
    kpi_data, year, category, region, status = _get_filtered_data()

    trend_chart_b64 = charts.generate_revenue_trend_chart(kpi_data["monthly_trends"])
    category_chart_b64 = charts.generate_category_comparison_chart(kpi_data["categories"])
    region_chart_b64 = charts.generate_regional_distribution_chart(kpi_data["regions"])

    return render_template(
        "analytics.html",
        active_page="analytics",
        kpis=kpi_data["kpis"],
        monthly_trends=kpi_data["monthly_trends"],
        categories=kpi_data["categories"],
        regions=kpi_data["regions"],
        matrix_regions=kpi_data["matrix_regions"],
        category_region_matrix=kpi_data["category_region_matrix"],
        month_comparison=kpi_data["month_comparison"],
        top_category=kpi_data["top_category"],
        top_region=kpi_data["top_region"],
        selected_year=year,
        selected_category=category,
        selected_region=region,
        selected_status=status,
        trend_chart_b64=trend_chart_b64,
        category_chart_b64=category_chart_b64,
        region_chart_b64=region_chart_b64
    )


@app.route("/report")
@login_required
def report_view():
    """Printable Executive KPI Report with 4-Quadrant Matplotlib Overview."""
    records = fetch_raw_data()
    overall_kpi_data = calculate_kpis(records)
    exec_chart_b64 = charts.generate_consolidated_executive_figure(overall_kpi_data)

    return render_template(
        "report.html",
        active_page="report",
        kpis=overall_kpi_data["kpis"],
        exec_chart_b64=exec_chart_b64
    )


@app.route("/database")
@login_required
def database_view():
    """Database Configuration & Schema Inspection."""
    return render_template(
        "database.html",
        active_page="database"
    )


@app.route("/database/configure-mysql", methods=["POST"])
@login_required
def configure_mysql():
    """Handles MySQL connection testing, switching, and SQLite migration."""
    action = request.form.get("action")
    host = request.form.get("host", "localhost").strip()
    port = int(request.form.get("port", 3306))
    user = request.form.get("user", "root").strip()
    password = request.form.get("password", "")
    database = request.form.get("database", "ecommerce_bi").strip()

    if action == "test":
        success, msg = test_mysql_connection(host, port, user, password, database)
        if success:
            flash(f"Connection Successful! Verified connectivity to MySQL on {host}:{port}.", "success")
        else:
            flash(f"MySQL Connection Failed: {msg}", "danger")

    elif action == "switch":
        success, msg = test_mysql_connection(host, port, user, password, database)
        if success:
            CURRENT_CONFIG["db_type"] = "mysql"
            CURRENT_CONFIG["mysql_host"] = host
            CURRENT_CONFIG["mysql_port"] = port
            CURRENT_CONFIG["mysql_user"] = user
            CURRENT_CONFIG["mysql_password"] = password
            CURRENT_CONFIG["mysql_database"] = database
            init_db()
            seed_data()
            flash("Active database successfully switched to MySQL!", "success")
        else:
            flash(f"Cannot switch: MySQL test failed ({msg})", "danger")

    elif action == "migrate":
        success, msg = migrate_sqlite_to_mysql(host, port, user, password, database)
        if success:
            flash(f"Migration Complete! {msg}", "success")
        else:
            flash(f"Migration Failed: {msg}", "danger")

    return redirect(url_for("database_view"))


@app.route("/database/switch-sqlite", methods=["POST"])
@login_required
def switch_to_sqlite():
    """Switches active database back to SQLite."""
    CURRENT_CONFIG["db_type"] = "sqlite"
    flash("Switched active database back to SQLite (local file engine).", "info")
    return redirect(url_for("database_view"))


@app.route("/database/reseed", methods=["POST"])
@login_required
def reseed_database():
    """Clears and reseeds sample e-commerce data."""
    try:
        from database import SQLITE_DB_PATH
        if CURRENT_CONFIG["db_type"] == "sqlite" and os.path.exists(SQLITE_DB_PATH):
            os.remove(SQLITE_DB_PATH)
        seed_data(target_orders=2200)
        flash("Successfully regenerated 2,200 fresh sample BI orders and line items!", "success")
    except Exception as e:
        flash(f"Error resetting database: {e}", "danger")
    return redirect(url_for("database_view"))


@app.route("/export/csv")
@login_required
def export_csv():
    """Generates downloadable CSV for monthly financial ledger."""
    kpi_data, _, _, _, _ = _get_filtered_data()
    monthly = kpi_data["monthly_trends"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Month", "Gross Sales ($)", "Discounts ($)", "Returns ($)", 
        "Net Sales ($)", "MoM Net Growth (%)", "Valid Order Count", 
        "MoM Order Growth (%)", "Net AOV ($)", "Total Units Sold", "Cancelled Orders"
    ])

    for row in monthly:
        writer.writerow([
            row["month"],
            row["gross_sales"],
            row["discounts"],
            row["returns"],
            row["net_sales"],
            row["mom_net_growth_pct"],
            row["order_count"],
            row["mom_order_growth_pct"],
            row["aov"],
            row["units_sold"],
            row["cancelled_orders"]
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=ecommerce_bi_monthly_report.csv"}
    )


@app.route("/api/kpis")
@login_required
def api_kpis():
    """JSON API endpoint for programmatic KPI retrieval."""
    kpi_data, _, _, _, _ = _get_filtered_data()
    return jsonify(kpi_data)


# Auto-initialize database on startup (ensures DB tables & demo admin are ready under Gunicorn & WSGI)
try:
    init_db()
    seed_data(target_orders=2200)
except Exception as e:
    app.logger.warning(f"Database auto-initialization notice: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1")
    print(f"OmniStore Business Intelligence Dashboard running on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
