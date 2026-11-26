
import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)
import re
import sqlite3
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from database import get_db, close_db, init_db, seed_products


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.teardown_appcontext(close_db)

    # ---------------- GLOBAL TEMPLATE VARIABLES ----------------

    @app.context_processor
    def inject_globals():
        cart_count = 0

        if session.get("user_id"):
            row = get_db().execute(
                "SELECT COALESCE(SUM(quantity),0) AS n "
                "FROM cart_items WHERE user_id=?",
                (session["user_id"],)
            ).fetchone()

            cart_count = row["n"]

        return {"cart_count": cart_count}

    # ---------------- LOGIN REQUIRED ----------------

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please sign in to continue.", "info")
                return redirect(
                    url_for("login", next=request.path)
                )

            return view(*args, **kwargs)

        return wrapped

    # ---------------- ADMIN REQUIRED ----------------

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") != "admin":
                abort(403)

            return view(*args, **kwargs)

        return wrapped

    # ---------------- CURRENCY FILTER ----------------

    @app.template_filter("inr")
    def inr(value):
        return "₹{:,.2f}".format(value or 0)

    # ---------------- HOME PAGE ----------------

    @app.route("/")
    def home():
        db = get_db()

        featured = db.execute(
            """
            SELECT * FROM products
            WHERE active=1 AND featured=1
            ORDER BY id DESC LIMIT 4
            """
        ).fetchall()

        categories = db.execute(
            """
            SELECT DISTINCT category FROM products
            WHERE active=1 ORDER BY category
            """
        ).fetchall()

        return render_template(
            "index.html",
            featured=featured,
            categories=categories
        )

    # ---------------- PRODUCTS PAGE ----------------

    @app.route("/products")
    def products():
        db = get_db()

        search = request.args.get("search", "").strip()
        category = request.args.get("category", "").strip()
        sort = request.args.get("sort", "newest")

        sql = "SELECT * FROM products WHERE active=1"
        params = []

        if search:
            sql += " AND (name LIKE ? OR description LIKE ? OR category LIKE ?)"
            params += [f"%{search}%"] * 3

        if category:
            sql += " AND category=?"
            params.append(category)

        order = {
            "price_low": "price ASC",
            "price_high": "price DESC",
            "name": "name COLLATE NOCASE ASC",
            "newest": "id DESC"
        }.get(sort, "id DESC")

        items = db.execute(
            sql + " ORDER BY " + order,
            params
        ).fetchall()

        categories = db.execute(
            """
            SELECT DISTINCT category FROM products
            WHERE active=1 ORDER BY category
            """
        ).fetchall()

        return render_template(
            "products.html",
            products=items,
            categories=categories,
            search=search,
            category=category,
            sort=sort
        )

    # ---------------- PRODUCT DETAILS ----------------

    @app.route("/product/<slug>")
    def product_detail(slug):
        product = get_db().execute(
            "SELECT * FROM products WHERE slug=? AND active=1",
            (slug,)
        ).fetchone()

        if product is None:
            abort(404)

        return render_template(
            "product_detail.html",
            product=product
        )

    # ---------------- REGISTER ----------------

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":

            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if len(name) < 2 or len(name) > 80:
                flash(
                    "Enter a name between 2 and 80 characters.",
                    "error"
                )

            elif not re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+",
                email
            ):
                flash("Enter a valid email address.", "error")

            elif len(password) < 8:
                flash(
                    "Password must contain at least 8 characters.",
                    "error"
                )

            else:
                try:
                    db = get_db()

                    cur = db.execute(
                        """
                        INSERT INTO users(name,email,password_hash)
                        VALUES(?,?,?)
                        """,
                        (
                            name,
                            email,
                            generate_password_hash(password)
                        )
                    )

                    db.commit()

                    session.clear()
                    session.update(
                        user_id=cur.lastrowid,
                        name=name,
                        role="customer"
                    )

                    flash(
                        "Your account has been created.",
                        "success"
                    )

                    return redirect(url_for("home"))

                except sqlite3.IntegrityError:
                    flash(
                        "An account with this email already exists.",
                        "error"
                    )

        return render_template("register.html")

    # ---------------- LOGIN ----------------

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":

            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            user = get_db().execute(
                "SELECT * FROM users WHERE email=?",
                (email,)
            ).fetchone()

            if user and check_password_hash(
                user["password_hash"],
                password
            ):
                session.clear()

                session.update(
                    user_id=user["id"],
                    name=user["name"],
                    role=user["role"]
                )

                flash("Welcome back!", "success")

                target = request.args.get("next", "")

                if not target.startswith("/") or target.startswith("//"):
                    target = url_for("home")

                return redirect(target)

            flash("Invalid email or password.", "error")

        return render_template("login.html")

    # ---------------- LOGOUT ----------------

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()

        flash("You have been signed out.", "success")

        return redirect(url_for("home"))

    # ---------------- SHOPPING CART ----------------

    @app.route("/cart")
    @login_required
    def cart():
        rows = get_db().execute(
            """
            SELECT c.quantity,p.* FROM cart_items c
            JOIN products p ON p.id=c.product_id
            WHERE c.user_id=?
            ORDER BY c.id DESC
            """,
            (session["user_id"],)
        ).fetchall()

        total = sum(
            row["price"] * row["quantity"]
            for row in rows
        )

        return render_template(
            "cart.html",
            items=rows,
            total=total
        )

    # ---------------- ADD TO CART ----------------

    @app.post("/cart/add/<int:product_id>")
    @login_required
    def add_to_cart(product_id):
        db = get_db()

        product = db.execute(
            "SELECT * FROM products WHERE id=? AND active=1",
            (product_id,)
        ).fetchone()

        if product is None:
            abort(404)

        try:
            quantity = max(
                1,
                min(int(request.form.get("quantity", 1)), 20)
            )
        except ValueError:
            quantity = 1

        if product["stock"] < quantity:
            flash("Not enough stock is available.", "error")

        else:
            db.execute(
                """
                INSERT INTO cart_items(user_id,product_id,quantity)
                VALUES(?,?,?)
                ON CONFLICT(user_id,product_id)
                DO UPDATE SET quantity=MIN(quantity+excluded.quantity,20)
                """,
                (session["user_id"], product_id, quantity)
            )

            db.commit()

            flash("Added to your cart.", "success")

        return redirect(request.referrer or url_for("cart"))

    # ---------------- UPDATE CART ----------------

    @app.post("/cart/update/<int:product_id>")
    @login_required
    def update_cart(product_id):
        db = get_db()

        try:
            quantity = int(request.form.get("quantity", 1))
        except ValueError:
            quantity = 1

        if quantity <= 0:
            db.execute(
                """
                DELETE FROM cart_items
                WHERE user_id=? AND product_id=?
                """,
                (session["user_id"], product_id)
            )

        else:
            product = db.execute(
                "SELECT stock FROM products WHERE id=?",
                (product_id,)
            ).fetchone()

            if product and quantity <= product["stock"] and quantity <= 20:
                db.execute(
                    """
                    UPDATE cart_items SET quantity=?
                    WHERE user_id=? AND product_id=?
                    """,
                    (quantity, session["user_id"], product_id)
                )

            else:
                flash(
                    "Requested quantity is not available.",
                    "error"
                )

        db.commit()

        return redirect(url_for("cart"))

    # ---------------- REMOVE FROM CART ----------------

    @app.post("/cart/remove/<int:product_id>")
    @login_required
    def remove_from_cart(product_id):
        db = get_db()

        db.execute(
            """
            DELETE FROM cart_items
            WHERE user_id=? AND product_id=?
            """,
            (session["user_id"], product_id)
        )

        db.commit()

        flash("Item removed from cart.", "success")

        return redirect(url_for("cart"))

    # ---------------- CHECKOUT ----------------

    @app.route("/checkout", methods=["GET", "POST"])
    @login_required
    def checkout():
        db = get_db()

        items = db.execute(
            """
            SELECT c.quantity,p.* FROM cart_items c
            JOIN products p ON p.id=c.product_id
            WHERE c.user_id=? AND p.active=1
            """,
            (session["user_id"],)
        ).fetchall()

        if not items:
            flash("Your cart is empty.", "info")
            return redirect(url_for("products"))

        total = sum(
            item["price"] * item["quantity"]
            for item in items
        )

        if request.method == "POST":

            fields = {
                key: request.form.get(key, "").strip()
                for key in (
                    "customer_name",
                    "phone",
                    "address",
                    "city",
                    "postal_code"
                )
            }

            if not all(fields.values()):
                flash(
                    "Please complete all delivery details.",
                    "error"
                )

            elif not re.fullmatch(
                r"[0-9+\-\s]{8,16}",
                fields["phone"]
            ):
                flash("Enter a valid phone number.", "error")

            else:
                try:
                    db.execute("BEGIN IMMEDIATE")

                    for item in items:
                        current = db.execute(
                            "SELECT stock FROM products WHERE id=?",
                            (item["id"],)
                        ).fetchone()

                        if (
                            current is None
                            or current["stock"] < item["quantity"]
                        ):
                            raise ValueError(
                                "One or more products no longer have enough stock."
                            )

                    cur = db.execute(
                        """
                        INSERT INTO orders
                        (
                            user_id,total,customer_name,phone,
                            address,city,postal_code
                        )
                        VALUES(?,?,?,?,?,?,?)
                        """,
                        (
                            session["user_id"],
                            total,
                            fields["customer_name"],
                            fields["phone"],
                            fields["address"],
                            fields["city"],
                            fields["postal_code"]
                        )
                    )

                    order_id = cur.lastrowid

                    for item in items:
                        db.execute(
                            """
                            INSERT INTO order_items
                            (
                                order_id,product_id,product_name,
                                unit_price,quantity
                            )
                            VALUES(?,?,?,?,?)
                            """,
                            (
                                order_id,
                                item["id"],
                                item["name"],
                                item["price"],
                                item["quantity"]
                            )
                        )

                        db.execute(
                            "UPDATE products SET stock=stock-? WHERE id=?",
                            (item["quantity"], item["id"])
                        )

                    db.execute(
                        "DELETE FROM cart_items WHERE user_id=?",
                        (session["user_id"],)
                    )

                    db.commit()

                    flash(
                        f"Order #{order_id} placed successfully. "
                        "Payment is Cash on Delivery.",
                        "success"
                    )

                    return redirect(url_for("orders"))

                except ValueError as exc:
                    db.rollback()
                    flash(str(exc), "error")

                except sqlite3.Error:
                    db.rollback()
                    flash(
                        "We could not place your order. Please try again.",
                        "error"
                    )

        return render_template(
            "checkout.html",
            items=items,
            total=total
        )

    # ---------------- ORDER HISTORY ----------------

    @app.route("/orders")
    @login_required
    def orders():
        rows = get_db().execute(
            """
            SELECT * FROM orders
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (session["user_id"],)
        ).fetchall()

        return render_template(
            "orders.html",
            orders=rows
        )

    # ---------------- ORDER DETAILS ----------------

    @app.route("/orders/<int:order_id>")
    @login_required
    def order_detail(order_id):
        db = get_db()

        order = db.execute(
            """
            SELECT * FROM orders
            WHERE id=? AND user_id=?
            """,
            (order_id, session["user_id"])
        ).fetchone()

        if order is None:
            abort(404)

        items = db.execute(
            "SELECT * FROM order_items WHERE order_id=?",
            (order_id,)
        ).fetchall()

        return render_template(
            "order_detail.html",
            order=order,
            items=items
        )

    # ---------------- ADMIN DASHBOARD ----------------

    @app.route("/admin")
    @admin_required
    def admin():
        db = get_db()

        stats = {
            "products": db.execute(
                "SELECT COUNT(*) FROM products"
            ).fetchone()[0],

            "orders": db.execute(
                "SELECT COUNT(*) FROM orders"
            ).fetchone()[0],

            "users": db.execute(
                "SELECT COUNT(*) FROM users WHERE role='customer'"
            ).fetchone()[0],

            "revenue": db.execute(
                "SELECT COALESCE(SUM(total),0) FROM orders"
            ).fetchone()[0]
        }

        products = db.execute(
            "SELECT * FROM products ORDER BY id DESC"
        ).fetchall()

        orders = db.execute(
            """
            SELECT o.*,u.email FROM orders o
            JOIN users u ON u.id=o.user_id
            ORDER BY o.id DESC LIMIT 30
            """
        ).fetchall()

        return render_template(
            "admin.html",
            stats=stats,
            products=products,
            orders=orders
        )

    # ---------------- ADD / EDIT PRODUCT ----------------

    @app.route("/admin/products/new", methods=["GET", "POST"])
    @app.route(
        "/admin/products/<int:product_id>/edit",
        methods=["GET", "POST"]
    )
    @admin_required
    def admin_product_form(product_id=None):
        db = get_db()

        product = (
            db.execute(
                "SELECT * FROM products WHERE id=?",
                (product_id,)
            ).fetchone()
            if product_id else None
        )

        if product_id and product is None:
            abort(404)

        if request.method == "POST":

            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()
            category = request.form.get("category", "").strip()
            image_url = request.form.get("image_url", "").strip()

            try:
                price = float(request.form.get("price", "0"))
                stock = int(request.form.get("stock", "0"))
            except ValueError:
                price, stock = -1, -1

            if not name or not category or price < 0 or stock < 0:
                flash(
                    "Enter a product name, category, valid price and stock.",
                    "error"
                )

            else:
                slug = re.sub(
                    r"[^a-z0-9]+",
                    "-",
                    name.lower()
                ).strip("-")

                if product:
                    db.execute(
                        """
                        UPDATE products
                        SET name=?,slug=?,description=?,price=?,
                            category=?,image_url=?,stock=?,
                            featured=?,active=?
                        WHERE id=?
                        """,
                        (
                            name,
                            f"{slug}-{product_id}",
                            description,
                            price,
                            category,
                            image_url,
                            stock,
                            int(bool(request.form.get("featured"))),
                            int(bool(request.form.get("active"))),
                            product_id
                        )
                    )

                else:
                    db.execute(
                        """
                        INSERT INTO products
                        (
                            name,slug,description,price,
                            category,image_url,stock,featured
                        )
                        VALUES(?,?,?,?,?,?,?,?)
                        """,
                        (
                            name,
                            f"{slug}-{os.urandom(3).hex()}",
                            description,
                            price,
                            category,
                            image_url,
                            stock,
                            int(bool(request.form.get("featured")))
                        )
                    )

                db.commit()

                flash("Product saved.", "success")

                return redirect(url_for("admin"))

        return render_template(
            "admin_product_form.html",
            product=product
        )

    # ---------------- HIDE PRODUCT ----------------

    @app.post("/admin/products/<int:product_id>/delete")
    @admin_required
    def admin_product_delete(product_id):
        db = get_db()

        db.execute(
            "UPDATE products SET active=0 WHERE id=?",
            (product_id,)
        )

        db.commit()

        flash("Product hidden from the store.", "success")

        return redirect(url_for("admin"))

    # ---------------- UPDATE ORDER STATUS ----------------

    @app.post("/admin/orders/<int:order_id>/status")
    @admin_required
    def admin_order_status(order_id):
        status = request.form.get("status", "")

        if status not in (
            "Placed",
            "Processing",
            "Shipped",
            "Delivered",
            "Cancelled"
        ):
            abort(400)

        db = get_db()

        db.execute(
            "UPDATE orders SET status=? WHERE id=?",
            (status, order_id)
        )

        db.commit()

        flash("Order status updated.", "success")

        return redirect(url_for("admin"))

    # ---------------- ERROR PAGES ----------------

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template(
            "error.html",
            code=403,
            message="You do not have permission to view this page."
        ), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            "error.html",
            code=404,
            message="The page you are looking for could not be found."
        ), 404

    # ---------------- DATABASE INITIALIZATION ----------------

    with app.app_context():

        init_db()
        seed_products()

        # Create or update the admin account using .env settings.
        admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        admin_password = os.getenv("ADMIN_PASSWORD", "")

        if admin_email and admin_password:

            db = get_db()

            existing = db.execute(
                "SELECT id, role FROM users WHERE email=?",
                (admin_email,)
            ).fetchone()

            password_hash = generate_password_hash(admin_password)

            if existing:
                db.execute(
                    """
                    UPDATE users
                    SET role='admin', password_hash=?
                    WHERE id=?
                    """,
                    (password_hash, existing["id"])
                )

            else:
                db.execute(
                    """
                    INSERT INTO users
                    (name,email,password_hash,role)
                    VALUES(?,?,?,'admin')
                    """,
                    (
                        "NovaCart Admin",
                        admin_email,
                        password_hash
                    )
                )

            db.commit()

        else:
            app.logger.warning(
                "ADMIN_EMAIL or ADMIN_PASSWORD is missing from .env"
            )

    return app


# ---------------- RUN APPLICATION ----------------

app = create_app()

if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "False").lower() == "true"
    )
