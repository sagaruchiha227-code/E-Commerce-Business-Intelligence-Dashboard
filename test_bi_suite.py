"""
Comprehensive Unit & Integration Test Suite for E-Commerce BI Dashboard.
Verifies:
1. Database schema, tables, and seeding integrity.
2. User authentication, password hashing, session management, and route protection.
3. Accurate KPI formulas (Gross, Net, Discounts, Returns, Order Count, AOV).
4. Multi-item order distinct count deduplication.
5. Missing/null value imputation (0.00 default).
6. Zero-revenue previous period division safety.
7. Matplotlib chart rendering engines.
8. All public and authenticated HTTP endpoints.
"""

import unittest
from app import app
from database import (
    init_db,
    seed_data,
    fetch_raw_data,
    create_user,
    get_user_by_email_or_username,
    seed_default_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from kpi_engine import calculate_kpis
import charts


class TestEcommerceBISuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n=======================================================")
        print("Starting E-Commerce BI Suite Automated Verification")
        print("=======================================================")
        init_db()
        seed_data(target_orders=500)
        seed_default_user()
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_01_database_seeding(self):
        """Verifies database contains normalized orders, products, and order_items."""
        records = fetch_raw_data()
        self.assertGreater(len(records), 0, "Database should contain records.")
        sample = records[0]
        self.assertIn("order_id", sample)
        self.assertIn("order_date", sample)
        self.assertIn("order_status", sample)
        self.assertIn("region", sample)
        self.assertIn("category", sample)
        self.assertIn("quantity", sample)
        self.assertIn("unit_price", sample)
        print(f"[PASS] Database contains {len(records)} normalized line items.")

    def test_02_user_auth_and_password_hashing(self):
        """Verifies secure user registration, password hashing, and credentials lookup."""
        import time
        # Test default user
        admin = get_user_by_email_or_username("admin@omnistore.bi")
        self.assertIsNotNone(admin, "Default admin user must exist.")
        self.assertTrue(check_password_hash(admin["password_hash"], "Admin123!"), "Password hash verification failed.")

        # Test new user registration with unique timestamp identifier
        ts = int(time.time() * 1000)
        email = f"analyst_{ts}@omnistore.bi"
        username = f"analyst_{ts}"
        raw_pwd = "ExecutiveSecret2026!"
        h_pwd = generate_password_hash(raw_pwd)
        success, user_id = create_user("Test Analyst", email, username, h_pwd, role="BI Analyst")
        self.assertTrue(success, f"New user creation must succeed: {user_id}")

        user = get_user_by_email_or_username(username)
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], email)
        self.assertTrue(check_password_hash(user["password_hash"], raw_pwd))

        # Reject duplicate email
        dup_success, _ = create_user("Duplicate User", email, f"dup_{ts}", h_pwd)
        self.assertFalse(dup_success, "Duplicate email registration must be rejected.")
        print("[PASS] User authentication & password hashing verified.")

    def test_03_route_access_protection(self):
        """Verifies that protected routes redirect unauthenticated users to login."""
        protected_routes = ["/dashboard", "/analytics", "/report", "/database", "/export/csv"]
        for route in protected_routes:
            res = self.client.get(route, follow_redirects=False)
            self.assertEqual(res.status_code, 302, f"Unauthenticated access to {route} should redirect to /login")
            self.assertIn("/login", res.headers.get("Location", ""))

        # Public routes should be accessible without login
        public_routes = ["/", "/login", "/register", "/documentation"]
        for route in public_routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Public route {route} should return 200 OK")
        print("[PASS] Route access protection verified (unauthenticated redirected to /login).")

    def test_04_authenticated_session_flow(self):
        """Verifies login, session persistence, and authenticated page access."""
        with self.client:
            # Login as default admin
            login_res = self.client.post("/login", data={
                "identifier": "admin@omnistore.bi",
                "password": "Admin123!"
            }, follow_redirects=True)
            self.assertEqual(login_res.status_code, 200)

            # Access protected dashboard
            dash_res = self.client.get("/dashboard")
            self.assertEqual(dash_res.status_code, 200, "Authenticated user should access /dashboard with 200 OK")
            self.assertIn(b"Executive KPI Dashboard", dash_res.data)

            # Access protected sales analytics
            analytics_res = self.client.get("/analytics")
            self.assertEqual(analytics_res.status_code, 200, "Authenticated user should access /analytics with 200 OK")
            self.assertIn(b"Sales & Revenue Analytics", analytics_res.data)

            # Logout
            logout_res = self.client.get("/logout", follow_redirects=True)
            self.assertEqual(logout_res.status_code, 200)

            # Subsequent dashboard access should redirect again
            subsequent_res = self.client.get("/dashboard", follow_redirects=False)
            self.assertEqual(subsequent_res.status_code, 302)
        print("[PASS] Authenticated session lifecycle (Login -> Access -> Logout) verified.")

    def test_05_kpi_accounting_formula_integrity(self):
        """Verifies strict accounting formula consistency: Net Sales = Gross Sales - Discounts - Returns."""
        records = fetch_raw_data()
        res = calculate_kpis(records)
        kpis = res["kpis"]

        # Net Sales = Gross - Discounts - Returns
        calc_net = round(kpis["total_gross_sales"] - kpis["total_discounts"] - kpis["total_returns"], 2)
        self.assertAlmostEqual(kpis["total_net_sales"], calc_net, delta=0.05,
                               msg=f"Net Sales mismatch: expected {calc_net}, got {kpis['total_net_sales']}")

        # AOV = Net Sales / Order Count
        if kpis["order_count"] > 0:
            calc_aov = round(kpis["total_net_sales"] / kpis["order_count"], 2)
            self.assertAlmostEqual(kpis["aov_net"], calc_aov, delta=0.05,
                                   msg=f"AOV mismatch: expected {calc_aov}, got {kpis['aov_net']}")

        # Cancellation rate within bounds
        self.assertGreaterEqual(kpis["cancellation_rate"], 0.0)
        self.assertLessEqual(kpis["cancellation_rate"], 100.0)
        print(f"[PASS] KPI formulas verified. Net Sales: ${kpis['total_net_sales']:,.2f}, Orders: {kpis['order_count']}, Net AOV: ${kpis['aov_net']:,.2f}")

    def test_06_cancelled_orders_exclusion(self):
        """Ensures cancelled orders do not inflate revenue or valid order counts."""
        synthetic_records = [
            {"order_id": 9991, "order_date": "2026-05-01", "order_status": "Delivered", "region": "North America",
             "category": "Electronics", "quantity": 1, "unit_price": 500.0, "discount_optional": 50.0, "return_amount_optional": 0.0},
            {"order_id": 9992, "order_date": "2026-05-02", "order_status": "Cancelled", "region": "North America",
             "category": "Electronics", "quantity": 2, "unit_price": 1000.0, "discount_optional": 100.0, "return_amount_optional": 0.0}
        ]
        res = calculate_kpis(synthetic_records)
        kpis = res["kpis"]
        self.assertEqual(kpis["total_gross_sales"], 500.0, "Cancelled order gross sales must be excluded.")
        self.assertEqual(kpis["total_net_sales"], 450.0, "Cancelled order net sales must be excluded.")
        self.assertEqual(kpis["order_count"], 1, "Cancelled order must not be counted in valid order count.")
        self.assertEqual(kpis["cancelled_orders"], 1, "Cancelled order must be captured in risk count.")
        self.assertEqual(kpis["cancellation_rate"], 50.0, "Cancellation rate should be 50%.")
        print("[PASS] Cancelled orders exclusion rule verified.")

    def test_07_multi_item_order_distinct_count(self):
        """Ensures an order containing multiple line items is counted as exactly 1 order."""
        multi_item_order = [
            {"order_id": 777, "order_date": "2026-06-01", "order_status": "Completed", "region": "Europe",
             "category": "Electronics", "quantity": 1, "unit_price": 200.0, "discount_optional": 0.0, "return_amount_optional": 0.0},
            {"order_id": 777, "order_date": "2026-06-01", "order_status": "Completed", "region": "Europe",
             "category": "Apparel & Fashion", "quantity": 2, "unit_price": 50.0, "discount_optional": 10.0, "return_amount_optional": 0.0},
            {"order_id": 777, "order_date": "2026-06-01", "order_status": "Completed", "region": "Europe",
             "category": "Home & Kitchen", "quantity": 1, "unit_price": 80.0, "discount_optional": 0.0, "return_amount_optional": 0.0}
        ]
        res = calculate_kpis(multi_item_order)
        kpis = res["kpis"]
        self.assertEqual(kpis["order_count"], 1, "Multiple line items with identical order_id must count as 1 order.")
        self.assertEqual(kpis["total_units_sold"], 4, "Total units sold must be 4.")
        self.assertEqual(kpis["total_gross_sales"], 380.0)
        self.assertEqual(kpis["total_net_sales"], 370.0)
        print("[PASS] Multi-product distinct order deduplication verified.")

    def test_08_missing_values_imputation_and_zero_baseline(self):
        """Ensures None/missing discount or return values and zero previous periods don't crash."""
        null_test_records = [
            {"order_id": 101, "order_date": "2026-01-01", "order_status": "Completed", "region": "North America",
             "category": "Electronics", "quantity": 1, "unit_price": 100.0, "discount_optional": None, "return_amount_optional": None},
            {"order_id": 102, "order_date": "2026-02-01", "order_status": "Completed", "region": "North America",
             "category": "Electronics", "quantity": 1, "unit_price": 200.0, "discount_optional": 0.0, "return_amount_optional": 0.0}
        ]
        res = calculate_kpis(null_test_records)
        kpis = res["kpis"]
        self.assertEqual(kpis["total_discounts"], 0.0)
        self.assertEqual(kpis["total_returns"], 0.0)
        self.assertEqual(kpis["total_net_sales"], 300.0)

        # MoM from Month 1 ($100) to Month 2 ($200) should be +100%
        monthly = res["monthly_trends"]
        self.assertEqual(len(monthly), 2)
        self.assertEqual(monthly[0]["mom_net_growth_pct"], 0.0)  # first month has no prior period
        self.assertEqual(monthly[1]["mom_net_growth_pct"], 100.0) # (200-100)/100 * 100 = 100%
        print("[PASS] Missing values imputation (COALESCE/0.0) & zero-division safe calculations verified.")

    def test_09_matplotlib_visualizations(self):
        """Verifies that all 4 Matplotlib chart renderers succeed and output Base64 PNGs."""
        records = fetch_raw_data()
        res = calculate_kpis(records)

        trend_b64 = charts.generate_revenue_trend_chart(res["monthly_trends"])
        self.assertIsNotNone(trend_b64)
        self.assertGreater(len(trend_b64), 500)

        cat_b64 = charts.generate_category_comparison_chart(res["categories"])
        self.assertIsNotNone(cat_b64)

        reg_b64 = charts.generate_regional_distribution_chart(res["regions"])
        self.assertIsNotNone(reg_b64)

        exec_b64 = charts.generate_consolidated_executive_figure(res)
        self.assertIsNotNone(exec_b64)
        print("[PASS] All 4 Matplotlib visualization renderers succeeded.")


if __name__ == "__main__":
    unittest.main()
