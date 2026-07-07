from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gymflow-dev-secret-change-this-before-real-use")

# DB_PATH can be overridden with an environment variable so it can point to a
# persistent volume when deployed (e.g. Railway). Defaults to a local file for
# running on your own computer.
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "gymflow.db"))

PLAN_PRICE = {"Monthly": 1500, "Quarterly": 4000, "Annual": 14000}
PLAN_DAYS = {"Monthly": 30, "Quarterly": 90, "Annual": 365}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        plan TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'paid',
        joined TEXT NOT NULL,
        expiry TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        trainer TEXT NOT NULL,
        time TEXT NOT NULL,
        capacity INTEGER NOT NULL,
        booked INTEGER NOT NULL DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        email TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL
    )""")

    # Seed classes only if table is empty (so re-running the app doesn't duplicate demo data)
    if conn.execute("SELECT COUNT(*) c FROM classes").fetchone()["c"] == 0:
        c.executemany(
            "INSERT INTO classes (name, trainer, time, capacity, booked) VALUES (?,?,?,?,0)",
            [
                ("Morning HIIT", "Aditi Rao", "Mon/Wed/Fri — 7:00 AM", 12),
                ("Strength Fundamentals", "Vikram Singh", "Tue/Thu — 6:30 PM", 10),
                ("Yoga Flow", "Meera Joshi", "Daily — 8:00 AM", 15),
            ],
        )

    if conn.execute("SELECT COUNT(*) c FROM staff").fetchone()["c"] == 0:
        c.executemany(
            "INSERT INTO staff (name, role, email) VALUES (?,?,?)",
            [
                ("Vikram Singh", "Trainer", "vikram@gymflow.com"),
                ("Anjali Deshpande", "Front Desk", "anjali@gymflow.com"),
            ],
        )

    conn.commit()
    conn.close()


# ==================== ADMIN ROUTES ====================

@app.route("/")
def home():
    return redirect(url_for("admin_dashboard"))


@app.route("/admin")
def admin_dashboard():
    conn = get_db()
    members = conn.execute("SELECT * FROM members").fetchall()
    classes = conn.execute("SELECT * FROM classes").fetchall()
    today = datetime.now().strftime("%Y-%m-%d")
    checkins_today = conn.execute(
        "SELECT COUNT(DISTINCT member_id) c FROM attendance WHERE timestamp LIKE ?",
        (today + "%",),
    ).fetchone()["c"]
    conn.close()
    return render_template(
        "admin_dashboard.html",
        members=members,
        classes=classes,
        checkins_today=checkins_today,
        active="dashboard",
    )


@app.route("/admin/members", methods=["GET", "POST"])
def admin_members():
    conn = get_db()
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        plan = request.form["plan"]
        status = request.form["status"]
        joined = datetime.now().strftime("%Y-%m-%d")
        expiry = (datetime.now() + timedelta(days=PLAN_DAYS[plan])).strftime("%Y-%m-%d")
        try:
            conn.execute(
                "INSERT INTO members (name, email, plan, status, joined, expiry) VALUES (?,?,?,?,?,?)",
                (name, email, plan, status, joined, expiry),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # email already exists — ignore duplicate for this simple prototype
        conn.close()
        return redirect(url_for("admin_members"))

    members = conn.execute("SELECT * FROM members ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_members.html", members=members, active="members")


@app.route("/admin/members/delete/<int:member_id>", methods=["POST"])
def admin_members_delete(member_id):
    conn = get_db()
    conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    conn.execute("DELETE FROM bookings WHERE member_id = ?", (member_id,))
    conn.execute("DELETE FROM attendance WHERE member_id = ?", (member_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_members"))


@app.route("/admin/classes", methods=["GET", "POST"])
def admin_classes():
    conn = get_db()
    if request.method == "POST":
        name = request.form["name"].strip()
        trainer = request.form["trainer"].strip()
        time_ = request.form["time"].strip()
        capacity = int(request.form["capacity"])
        conn.execute(
            "INSERT INTO classes (name, trainer, time, capacity, booked) VALUES (?,?,?,?,0)",
            (name, trainer, time_, capacity),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin_classes"))

    classes = conn.execute("SELECT * FROM classes ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_classes.html", classes=classes, active="classes")


@app.route("/admin/classes/delete/<int:class_id>", methods=["POST"])
def admin_classes_delete(class_id):
    conn = get_db()
    conn.execute("DELETE FROM classes WHERE id = ?", (class_id,))
    conn.execute("DELETE FROM bookings WHERE class_id = ?", (class_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_classes"))


@app.route("/admin/staff", methods=["GET", "POST"])
def admin_staff():
    conn = get_db()
    if request.method == "POST":
        name = request.form["name"].strip()
        role = request.form["role"]
        email = request.form["email"].strip()
        conn.execute(
            "INSERT INTO staff (name, role, email) VALUES (?,?,?)", (name, role, email)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin_staff"))

    staff = conn.execute("SELECT * FROM staff ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_staff.html", staff=staff, active="staff")


@app.route("/admin/staff/delete/<int:staff_id>", methods=["POST"])
def admin_staff_delete(staff_id):
    conn = get_db()
    conn.execute("DELETE FROM staff WHERE id = ?", (staff_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_staff"))


# ==================== MEMBER ROUTES ====================

@app.route("/member")
def member_login():
    return render_template("member_login.html")


@app.route("/member/register", methods=["POST"])
def member_register():
    name = request.form["name"].strip()
    email = request.form["email"].strip()
    plan = request.form["plan"]

    conn = get_db()
    existing = conn.execute("SELECT * FROM members WHERE email = ?", (email,)).fetchone()
    if existing:
        member_id = existing["id"]
    else:
        joined = datetime.now().strftime("%Y-%m-%d")
        expiry = (datetime.now() + timedelta(days=PLAN_DAYS[plan])).strftime("%Y-%m-%d")
        cur = conn.execute(
            "INSERT INTO members (name, email, plan, status, joined, expiry) VALUES (?,?,?,?,?,?)",
            (name, email, plan, "paid", joined, expiry),
        )
        conn.commit()
        member_id = cur.lastrowid
    conn.close()

    session["member_id"] = member_id
    return redirect(url_for("member_dashboard"))


@app.route("/member/dashboard")
def member_dashboard():
    member_id = session.get("member_id")
    if not member_id:
        return redirect(url_for("member_login"))

    conn = get_db()
    member = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    classes = conn.execute("SELECT * FROM classes").fetchall()
    my_bookings = {
        row["class_id"]
        for row in conn.execute(
            "SELECT class_id FROM bookings WHERE member_id = ?", (member_id,)
        ).fetchall()
    }
    attendance = conn.execute(
        "SELECT timestamp FROM attendance WHERE member_id = ? ORDER BY id DESC",
        (member_id,),
    ).fetchall()
    conn.close()

    days_left = (datetime.strptime(member["expiry"], "%Y-%m-%d") - datetime.now()).days

    return render_template(
        "member_portal.html",
        member=member,
        classes=classes,
        my_bookings=my_bookings,
        attendance=attendance,
        days_left=days_left,
    )


@app.route("/member/book/<int:class_id>", methods=["POST"])
def member_book(class_id):
    member_id = session.get("member_id")
    if not member_id:
        return redirect(url_for("member_login"))

    conn = get_db()
    existing = conn.execute(
        "SELECT * FROM bookings WHERE member_id=? AND class_id=?", (member_id, class_id)
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM bookings WHERE id = ?", (existing["id"],))
        conn.execute(
            "UPDATE classes SET booked = booked - 1 WHERE id = ? AND booked > 0", (class_id,)
        )
    else:
        cls = conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
        if cls and cls["booked"] < cls["capacity"]:
            conn.execute(
                "INSERT INTO bookings (member_id, class_id) VALUES (?,?)", (member_id, class_id)
            )
            conn.execute("UPDATE classes SET booked = booked + 1 WHERE id = ?", (class_id,))

    conn.commit()
    conn.close()
    return redirect(url_for("member_dashboard"))


@app.route("/member/checkin", methods=["POST"])
def member_checkin():
    member_id = session.get("member_id")
    if not member_id:
        return redirect(url_for("member_login"))

    conn = get_db()
    conn.execute(
        "INSERT INTO attendance (member_id, timestamp) VALUES (?,?)",
        (member_id, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("member_dashboard"))


@app.route("/member/logout")
def member_logout():
    session.pop("member_id", None)
    return redirect(url_for("member_login"))


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
