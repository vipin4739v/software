from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secret123"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "crm.db")

import sqlite3

# ================= DATABASE =================
def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # ================= AGENTS TABLE =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT,
        created_by TEXT
    )
    """)

    # ================= LEADS BASE TABLE =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project TEXT,
        customer TEXT,
        mobile TEXT,
        email TEXT,
        property_type TEXT,
        category TEXT,
        source TEXT,
        enquiry_type TEXT,
        enquiry_from TEXT,
        budget_min TEXT,
        budget_max TEXT,
        stage TEXT,
        status TEXT,
        enquiry_date TEXT,
        next_follow TEXT,
        meeting_date TEXT,
        expected_closing TEXT,
        owner TEXT,
        handled_by TEXT,
        followup_type TEXT,
        last_followed TEXT,
        remarks TEXT,
        created_by TEXT
    )
    """)

    # ================= REQUIRED COLUMNS (AUTO MIGRATION) =================
    required_columns = {
        "project": "TEXT",
        "customer": "TEXT",
        "mobile": "TEXT",
        "email": "TEXT",
        "property_type": "TEXT",
        "category": "TEXT",
        "source": "TEXT",
        "enquiry_type": "TEXT",
        "enquiry_from": "TEXT",
        "budget_min": "TEXT",
        "budget_max": "TEXT",
        "stage": "TEXT",
        "status": "TEXT",
        "enquiry_date": "TEXT",
        "next_follow": "TEXT",
        "meeting_date": "TEXT",
        "expected_closing": "TEXT",
        "owner": "TEXT",
        "handled_by": "TEXT",
        "followup_type": "TEXT",
        "last_followed": "TEXT",
        "remarks": "TEXT",
        "created_by": "TEXT"
    }

    # ================= CHECK EXISTING COLUMNS =================
    cur.execute("PRAGMA table_info(leads)")
    existing_columns = [row["name"] for row in cur.fetchall()]

    # ================= AUTO ADD MISSING COLUMNS =================
    for col, col_type in required_columns.items():
        if col not in existing_columns:
            cur.execute(f"ALTER TABLE leads ADD COLUMN {col} {col_type}")

    conn.commit()
    conn.close()



# ================= INIT ON STARTUP =================
init_db()


# ================= DEFAULT ADMIN =================
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123"

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Admin login
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session.update({
                "email": email,
                "role": "admin",
                "name": "Admin"
            })
            return redirect(url_for("dashboard"))

        # Agent / Manager / User
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM agents WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session.update({
                "email": user["email"],
                "role": user["role"],
                "name": user["name"]
            })
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid Login")

    return render_template("login.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        email=session["email"],
        role=session["role"],
        name=session["name"]
    )

# ================= ADD AGENT =================
@app.route("/add_agent", methods=["GET", "POST"])
def add_agent():
    if "email" not in session:
        return redirect(url_for("login"))

    role = session["role"]

    if role == "User":
        return "Access Denied", 403

    if request.method == "POST":
        new_role = request.form["role"]

        if role == "Manager" and new_role != "User":
            return "Manager can create only User", 403

        conn = get_db()
        conn.execute("""
        INSERT INTO agents (name,mobile,email,password,role,created_by)
        VALUES (?,?,?,?,?,?)
        """, (
            request.form["name"],
            request.form["mobile"],
            request.form["email"],
            request.form["password"],
            new_role,
            session["email"]
        ))
        conn.commit()
        conn.close()

        flash("Agent created successfully")
        return redirect(url_for("manage_agent"))

    return render_template("add_agent.html", role=role)

@app.route("/manage_agent")
def manage_agent():
    if "email" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ================= FETCH AGENTS =================
    if session["role"] == "admin":
        agents = cur.execute(
            "SELECT * FROM agents ORDER BY id DESC"
        ).fetchall()

        managers = cur.execute(
            "SELECT COUNT(*) FROM agents WHERE role='Manager'"
        ).fetchone()[0]

        users = cur.execute(
            "SELECT COUNT(*) FROM agents WHERE role='User'"
        ).fetchone()[0]

    elif session["role"] == "Manager":
        agents = cur.execute(
            "SELECT * FROM agents WHERE created_by=? ORDER BY id DESC",
            (session["email"],)
        ).fetchall()

        users = cur.execute(
            "SELECT COUNT(*) FROM agents WHERE role='User' AND created_by=?",
            (session["email"],)
        ).fetchone()[0]

        managers = 0   # ❌ manager ko manager count nahi dikhega

    conn.close()

    return render_template(
        "manage_agent.html",
        agents=agents,
        managers=managers,
        users=users,
        role=session["role"]
    )




#==========================add Lead =================
@app.route("/add_lead", methods=["GET", "POST"])
def add_lead():
    if "email" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO leads (
            project, customer, mobile, email, property_type,
            category, source, enquiry_type, enquiry_from,
            budget_min, budget_max, stage, status,
            enquiry_date, next_follow, meeting_date,
            expected_closing, owner, handled_by,
            followup_type, last_followed, remarks, created_by
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            request.form.get("project"),
            request.form.get("customer"),
            request.form.get("mobile"),
            request.form.get("email"),
            request.form.get("property_type"),
            request.form.get("category"),
            request.form.get("source"),
            request.form.get("enquiry_type"),
            request.form.get("enquiry_from"),
            request.form.get("budget_min"),
            request.form.get("budget_max"),
            request.form.get("stage"),
            request.form.get("status"),
            request.form.get("enquiry_date"),
            request.form.get("next_follow"),
            request.form.get("meeting_date"),
            request.form.get("expected_closing"),
            request.form.get("owner"),
            request.form.get("handled_by"),
            request.form.get("followup_type"),
            request.form.get("last_followed"),
            request.form.get("remarks"),
            session["email"]
        ))

        conn.commit()
        conn.close()

        flash("Lead added successfully")
        return redirect(url_for("manage_lead"))

    return render_template("add_lead.html", role=session["role"])

# ================= MANAGE LEAD =================
@app.route("/manage-lead")
def manage_lead():
    if "email" not in session:
        return redirect(url_for("login"))

    role = session["role"]
    email = session["email"]
    conn = get_db()

    if role == "admin":
        leads = conn.execute("SELECT * FROM leads").fetchall()

    elif role == "Manager":
        leads = conn.execute("""
        SELECT * FROM leads
        WHERE created_by IN (
            SELECT email FROM agents WHERE created_by=?
        )
        """, (email,)).fetchall()

    else:  # User
        leads = conn.execute(
            "SELECT * FROM leads WHERE created_by=?",
            (email,)
        ).fetchall()

    conn.close()
    return render_template("manage_lead.html", leads=leads, role=role)


#---=========================================================================================================

@app.route("/get_lead/<int:id>")
def get_lead(id):
    conn=get_db()
    lead=conn.execute("SELECT * FROM leads WHERE id=?",(id,)).fetchone()
    conn.close()
    return dict(lead)



@app.route("/update_lead",methods=["POST"])
def update_lead():
    data=request.form
    conn=get_db()
    conn.execute("""
      UPDATE leads SET
      project=?,customer=?,mobile=?,email=?,category=?,source=?,
      enquiry_type=?,followup_type=?,budget_min=?,budget_max=?,
      next_follow=?,stage=?,status=?,handled_by=?,owner=?,remarks=?
      WHERE id=?
    """,(
      data["project"],data["customer"],data["mobile"],data["email"],
      data["category"],data["source"],data["enquiry_type"],data["followup_type"],
      data["budget_min"],data["budget_max"],data["next_follow"],
      data["stage"],data["status"],data["handled_by"],data["owner"],
      data["remarks"],data["id"]
    ))
    conn.commit(); conn.close()
    return {"success":True}



@app.route("/download_leads")
def download_leads():
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")

    import pandas as pd
    from io import BytesIO
    from flask import send_file

    conn = get_db()

    if from_date and to_date:
        query = """
            SELECT * FROM leads
            WHERE enquiry_date BETWEEN ? AND ?
        """
        df = pd.read_sql(query, conn, params=(from_date, to_date))
    else:
        df = pd.read_sql("SELECT * FROM leads", conn)

    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False, sheet_name="Leads")
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f"leads_{from_date}_to_{to_date}.xlsx"
    )


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
