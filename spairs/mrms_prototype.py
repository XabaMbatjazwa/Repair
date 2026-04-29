import streamlit as st
import pandas as pd
from datetime import datetime, date
import sqlite3
import os
import base64
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# -------------------------------
# PAGE CONFIG
st.set_page_config(
    page_title="AutoFix Pro - Motor Repairs",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------
# DATABASE SETUP
DB_FILE = "autofix.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS customers
                 (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT, address TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vehicles
                 (id INTEGER PRIMARY KEY, customer_id INTEGER, customer_name TEXT,
                  make TEXT, model TEXT, year INTEGER, license_plate TEXT, vin TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS job_cards
                 (id INTEGER PRIMARY KEY, job_id INTEGER, vehicle_id INTEGER, customer_name TEXT,
                  vehicle TEXT, complaint TEXT, estimated_hours REAL, status TEXT,
                  created_date TEXT, completed_date TEXT, mechanic_notes TEXT,
                  actual_labor_hours REAL, estimated_parts TEXT, actual_parts_used TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS parts
                 (id INTEGER PRIMARY KEY, part_id INTEGER, name TEXT, sku TEXT,
                  price REAL, quantity INTEGER, reorder_level INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS next_ids
                 (prefix TEXT PRIMARY KEY, next_id INTEGER)''')
    conn.commit()
    conn.close()

def load_data():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, phone, email, address FROM customers")
    customers = {row[0]: {"id": row[0], "name": row[1], "phone": row[2], "email": row[3], "address": row[4]} for row in c.fetchall()}
    c.execute("SELECT id, customer_id, customer_name, make, model, year, license_plate, vin FROM vehicles")
    vehicles = [{"vehicle_id": row[0], "customer_id": row[1], "customer_name": row[2],
                 "make": row[3], "model": row[4], "year": row[5], "license_plate": row[6], "vin": row[7]} for row in c.fetchall()]
    c.execute("SELECT id, job_id, vehicle_id, customer_name, vehicle, complaint, estimated_hours, status, created_date, completed_date, mechanic_notes, actual_labor_hours, estimated_parts, actual_parts_used FROM job_cards")
    job_cards = []
    for row in c.fetchall():
        job = {
            "db_id": row[0], "job_id": row[1], "vehicle_id": row[2], "customer_name": row[3], "vehicle": row[4],
            "complaint": row[5], "estimated_hours": row[6], "status": row[7], "created_date": row[8],
            "completed_date": row[9], "mechanic_notes": row[10], "actual_labor_hours": row[11],
            "estimated_parts": eval(row[12]) if row[12] else [],
            "actual_parts_used": eval(row[13]) if row[13] else []
        }
        job_cards.append(job)
    c.execute("SELECT part_id, name, sku, price, quantity, reorder_level FROM parts")
    parts = [{"part_id": row[0], "name": row[1], "sku": row[2], "price": row[3], "quantity": row[4], "reorder_level": row[5]} for row in c.fetchall()]
    c.execute("SELECT prefix, next_id FROM next_ids")
    next_ids = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return customers, vehicles, job_cards, parts, next_ids

def save_customers(customers):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM customers")
    for cust in customers.values():
        c.execute("INSERT INTO customers (id, name, phone, email, address) VALUES (?,?,?,?,?)",
                  (cust["id"], cust["name"], cust["phone"], cust["email"], cust["address"]))
    conn.commit()
    conn.close()

def save_vehicles(vehicles):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM vehicles")
    for v in vehicles:
        c.execute("INSERT INTO vehicles (id, customer_id, customer_name, make, model, year, license_plate, vin) VALUES (?,?,?,?,?,?,?,?)",
                  (v["vehicle_id"], v["customer_id"], v["customer_name"], v["make"], v["model"], v["year"], v["license_plate"], v["vin"]))
    conn.commit()
    conn.close()

def save_job_cards(job_cards):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM job_cards")
    for job in job_cards:
        c.execute('''INSERT INTO job_cards 
                     (id, job_id, vehicle_id, customer_name, vehicle, complaint, estimated_hours, status, created_date, completed_date, mechanic_notes, actual_labor_hours, estimated_parts, actual_parts_used)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (job.get("db_id", job["job_id"]), job["job_id"], job["vehicle_id"], job["customer_name"], job["vehicle"],
                   job["complaint"], job["estimated_hours"], job["status"], job["created_date"], job.get("completed_date"),
                   job.get("mechanic_notes", ""), job.get("actual_labor_hours", 0), str(job.get("estimated_parts", [])), str(job.get("actual_parts_used", []))))
    conn.commit()
    conn.close()

def save_parts(parts):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM parts")
    for p in parts:
        c.execute("INSERT INTO parts (part_id, name, sku, price, quantity, reorder_level) VALUES (?,?,?,?,?,?)",
                  (p["part_id"], p["name"], p["sku"], p["price"], p["quantity"], p["reorder_level"]))
    conn.commit()
    conn.close()

def save_next_ids(next_ids):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM next_ids")
    for prefix, nid in next_ids.items():
        c.execute("INSERT INTO next_ids (prefix, next_id) VALUES (?,?)", (prefix, nid))
    conn.commit()
    conn.close()

def persist_all():
    save_customers(st.session_state.customers)
    save_vehicles(st.session_state.vehicles)
    save_job_cards(st.session_state.job_cards)
    save_parts(st.session_state.parts)
    save_next_ids(st.session_state.next_ids)

# -------------------------------
# INIT DATABASE AND SESSION STATE
init_db()
if "initialized" not in st.session_state:
    customers, vehicles, job_cards, parts, next_ids = load_data()
    st.session_state.customers = customers
    st.session_state.vehicles = vehicles
    st.session_state.job_cards = job_cards
    st.session_state.parts = parts
    st.session_state.next_ids = next_ids if next_ids else {"customer": 1, "vehicle": 1, "job": 1, "part": 1}
    st.session_state.initialized = True

def get_next_id(prefix):
    nid = st.session_state.next_ids.get(prefix, 1)
    st.session_state.next_ids[prefix] = nid + 1
    save_next_ids(st.session_state.next_ids)
    return nid

# -------------------------------
# CUSTOM CSS
st.markdown("""
<style>
    .main { padding: 0rem 1rem; }
    h1, h2, h3 { color: #1e3a8a; font-weight: 600; }
    .metric-card { background-color: #f8fafc; padding: 1rem; border-radius: 0.75rem; border-left: 4px solid #3b82f6; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    .metric-value { font-size: 2rem; font-weight: bold; color: #1e40af; }
    .metric-label { font-size: 0.9rem; color: #475569; margin-top: 0.25rem; }
    .badge-draft { background-color: #cbd5e1; color: #1e293b; padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.8rem; display: inline-block; }
    .badge-approved { background-color: #fef9c3; color: #854d0e; padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.8rem; display: inline-block; }
    .badge-inprogress { background-color: #bfdbfe; color: #1e40af; padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.8rem; display: inline-block; }
    .badge-completed { background-color: #bbf7d0; color: #166534; padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.8rem; display: inline-block; }
    .badge-paid { background-color: #d9f99d; color: #365314; padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.8rem; display: inline-block; }
    .stButton button { background-color: #2563eb; color: white; border-radius: 0.5rem; font-weight: 500; transition: 0.2s; }
    .stButton button:hover { background-color: #1e40af; color: white; }
    .streamlit-expanderHeader { background-color: #f1f5f9; border-radius: 0.5rem; font-weight: 500; }
    .dataframe { border-radius: 0.5rem; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

def get_status_badge(status):
    badges = {
        "Draft": '<span class="badge-draft">📄 Draft</span>',
        "Approved": '<span class="badge-approved">✅ Approved</span>',
        "In Progress": '<span class="badge-inprogress">🔧 In Progress</span>',
        "Completed": '<span class="badge-completed">✔️ Completed</span>',
        "Paid": '<span class="badge-paid">💰 Paid</span>'
    }
    return badges.get(status, status)

# -------------------------------
# SIDEBAR WITH LOGO
st.sidebar.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
logo_path = "logo.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    logo_path_jpg = "logo.jpg"
    if os.path.exists(logo_path_jpg):
        st.sidebar.image(logo_path_jpg, use_container_width=True)
    else:
        st.sidebar.markdown('<h2 style="color: #1e3a8a;">🔧 AutoFix Pro</h2>', unsafe_allow_html=True)
st.sidebar.markdown('<p style="color: #4b5563; font-size: 0.8rem;">Motor Repairs Management</p><hr>', unsafe_allow_html=True)
st.sidebar.markdown('</div>', unsafe_allow_html=True)

menu = st.sidebar.radio(
    "📋 Main Menu",
    ["🏠 Dashboard", "👥 Customers & Vehicles", "📝 Job Cards", "🔩 Parts Inventory", "💰 Invoicing & Reports"],
    index=0
)

# -------------------------------
# DASHBOARD
if menu == "🏠 Dashboard":
    st.markdown("<h1 style='text-align: center;'>📊 Dashboard</h1>", unsafe_allow_html=True)
    total_jobs = len(st.session_state.job_cards)
    completed_jobs = sum(1 for j in st.session_state.job_cards if j["status"] == "Completed")
    paid_jobs = sum(1 for j in st.session_state.job_cards if j["status"] == "Paid")
    low_stock = sum(1 for p in st.session_state.parts if p["quantity"] <= p["reorder_level"])
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{total_jobs}</div><div class="metric-label">📋 Total Jobs</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{completed_jobs}</div><div class="metric-label">✅ Completed</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{paid_jobs}</div><div class="metric-label">💰 Paid</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{low_stock}</div><div class="metric-label">⚠️ Low Stock Parts</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("📌 Recent Job Cards")
    recent = sorted(st.session_state.job_cards, key=lambda x: x["created_date"], reverse=True)[:5]
    if recent:
        for job in recent:
            badge = get_status_badge(job["status"])
            with st.expander(f"Job #{job['job_id']} – {job['vehicle']} – {job['customer_name']}"):
                st.markdown(badge, unsafe_allow_html=True)
                st.write(f"**Complaint:** {job['complaint']}")
                st.write(f"**Created:** {job['created_date']}")
                if job['status'] == 'Completed':
                    st.write("**Ready for invoicing!**")
    else:
        st.info("No job cards yet. Go to **Job Cards** to create one.")

# -------------------------------
# CUSTOMERS & VEHICLES
elif menu == "👥 Customers & Vehicles":
    st.markdown("<h1>👥 Customer & Vehicle Management</h1>", unsafe_allow_html=True)
    tabs = st.tabs(["➕ Register Customer", "🚗 Register Vehicle", "📋 Customer List"])
    with tabs[0]:
        with st.form("customer_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name *")
                phone = st.text_input("Phone")
            with col2:
                email = st.text_input("Email")
                address = st.text_area("Address")
            if st.form_submit_button("💾 Save Customer", use_container_width=True):
                if name:
                    cid = get_next_id("customer")
                    st.session_state.customers[cid] = {"id": cid, "name": name, "phone": phone, "email": email, "address": address}
                    save_customers(st.session_state.customers)
                    st.success(f"✅ Customer '{name}' added (ID: {cid})")
                    st.rerun()
                else:
                    st.error("Name is required.")
    with tabs[1]:
        if not st.session_state.customers:
            st.warning("Please register a customer first.")
        else:
            with st.form("vehicle_form", clear_on_submit=True):
                customer_options = {f"{c['name']} (ID: {cid})": cid for cid, c in st.session_state.customers.items()}
                selected = st.selectbox("Select Customer", list(customer_options.keys()))
                col1, col2 = st.columns(2)
                with col1:
                    make = st.text_input("Make")
                    model = st.text_input("Model")
                with col2:
                    year = st.number_input("Year", min_value=1900, max_value=2026, step=1)
                    license_plate = st.text_input("License Plate")
                if st.form_submit_button("🚗 Register Vehicle", use_container_width=True):
                    if make and model:
                        vid = get_next_id("vehicle")
                        new_vehicle = {
                            "vehicle_id": vid,
                            "customer_id": customer_options[selected],
                            "customer_name": selected.split(" (ID")[0],
                            "make": make,
                            "model": model,
                            "year": year,
                            "license_plate": license_plate,
                            "vin": ""
                        }
                        st.session_state.vehicles.append(new_vehicle)
                        save_vehicles(st.session_state.vehicles)
                        st.success(f"Vehicle {make} {model} added.")
                        st.rerun()
                    else:
                        st.error("Make and Model required.")
    with tabs[2]:
        if st.session_state.customers:
            for cid, cust in st.session_state.customers.items():
                with st.expander(f"👤 {cust['name']} ({cust['phone']})"):
                    st.write(f"📧 {cust['email']} | 🏠 {cust['address']}")
                    vehicles_of = [v for v in st.session_state.vehicles if v["customer_id"] == cid]
                    if vehicles_of:
                        st.write("**Vehicles:**")
                        for v in vehicles_of:
                            st.write(f"- {v['make']} {v['model']} ({v['year']}) – {v['license_plate']}")
                    else:
                        st.caption("No vehicles registered yet.")
        else:
            st.info("No customers yet.")

# -------------------------------
# JOB CARDS (FIXED: NO unsafe_allow_html on expander)
elif menu == "📝 Job Cards":
    st.markdown("<h1>📝 Job Card Management</h1>", unsafe_allow_html=True)
    with st.expander("➕ Create New Job Card", expanded=False):
        if not st.session_state.vehicles:
            st.error("Please register a vehicle first.")
        else:
            vehicle_options = {f"{v['customer_name']} - {v['make']} {v['model']} ({v['license_plate']})": v["vehicle_id"] for v in st.session_state.vehicles}
            selected_vehicle_label = st.selectbox("Select Vehicle", list(vehicle_options.keys()))
            complaint = st.text_area("Customer Complaint / Symptoms")
            estimated_hours = st.number_input("Estimated Labor Hours", min_value=0.5, step=0.5)
            if "estimate_parts" not in st.session_state:
                st.session_state.estimate_parts = []
            if st.session_state.parts:
                st.subheader("🔧 Estimate Parts")
                part_options = {f"{p['name']} (Stock: {p['quantity']})": p["part_id"] for p in st.session_state.parts}
                col1, col2 = st.columns(2)
                with col1:
                    selected_part = st.selectbox("Select Part", list(part_options.keys()))
                with col2:
                    qty = st.number_input("Quantity", min_value=1, value=1)
                if st.button("➕ Add to Estimate"):
                    part_id = part_options[selected_part]
                    part = next(p for p in st.session_state.parts if p["part_id"] == part_id)
                    st.session_state.estimate_parts.append({
                        "part_id": part_id, "name": part["name"],
                        "quantity": qty, "unit_price": part["price"],
                        "total": qty * part["price"]
                    })
                    st.success(f"Added {qty} x {part['name']}")
                if st.session_state.estimate_parts:
                    df_est = pd.DataFrame(st.session_state.estimate_parts)
                    st.dataframe(df_est[["name", "quantity", "unit_price", "total"]], use_container_width=True)
                    if st.button("🗑️ Clear Estimate"):
                        st.session_state.estimate_parts = []
                        st.rerun()
            if st.button("📌 Create Job Card", type="primary", use_container_width=True):
                if complaint:
                    job_id = get_next_id("job")
                    new_job = {
                        "job_id": job_id,
                        "vehicle_id": vehicle_options[selected_vehicle_label],
                        "customer_name": selected_vehicle_label.split(" - ")[0],
                        "vehicle": selected_vehicle_label,
                        "complaint": complaint,
                        "estimated_hours": estimated_hours,
                        "estimated_parts": st.session_state.estimate_parts.copy(),
                        "status": "Draft",
                        "created_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "completed_date": None,
                        "mechanic_notes": "",
                        "actual_parts_used": [],
                        "actual_labor_hours": 0
                    }
                    st.session_state.job_cards.append(new_job)
                    save_job_cards(st.session_state.job_cards)
                    st.session_state.estimate_parts = []
                    st.success(f"✅ Job Card #{job_id} created.")
                    st.rerun()
                else:
                    st.error("Please enter a complaint.")
    st.subheader("📋 Existing Job Cards")
    if not st.session_state.job_cards:
        st.info("No job cards yet.")
    else:
        status_filter = st.selectbox("Filter by Status", ["All", "Draft", "Approved", "In Progress", "Completed", "Paid"])
        filtered = [j for j in st.session_state.job_cards if status_filter == "All" or j["status"] == status_filter]
        for job in filtered:
            badge = get_status_badge(job["status"])
            with st.expander(f"Job #{job['job_id']} – {job['vehicle']} – {job['customer_name']}"):
                st.markdown(badge, unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Customer:** {job['customer_name']}")
                    st.markdown(f"**Complaint:** {job['complaint']}")
                    st.markdown(f"**Est. Hours:** {job['estimated_hours']}")
                with col2:
                    st.markdown(f"**Created:** {job['created_date']}")
                    if job['status'] == "Completed":
                        st.markdown(f"**Completed:** {job['completed_date']}")
                if job["status"] == "Draft":
                    if st.button(f"✅ Approve Job #{job['job_id']}"):
                        job["status"] = "Approved"
                        save_job_cards(st.session_state.job_cards)
                        st.rerun()
                elif job["status"] == "Approved":
                    if st.button(f"🔧 Start Work (In Progress)", key=f"start_{job['job_id']}"):
                        job["status"] = "In Progress"
                        save_job_cards(st.session_state.job_cards)
                        st.rerun()
                elif job["status"] == "In Progress":
                    st.subheader("🛠️ Mechanic Update")
                    notes = st.text_area("Work notes", value=job.get("mechanic_notes", ""), key=f"notes_{job['job_id']}")
                    actual_hours = st.number_input("Actual Labor Hours", min_value=0.0, step=0.5, key=f"hours_{job['job_id']}")
                    if st.session_state.parts:
                        part_use = {f"{p['name']} (Stock: {p['quantity']})": p for p in st.session_state.parts}
                        selected_use = st.selectbox("Part Used", list(part_use.keys()), key=f"use_{job['job_id']}")
                        use_qty = st.number_input("Quantity Used", min_value=1, step=1, key=f"qty_{job['job_id']}")
                        if st.button(f"➕ Add Used Part", key=f"add_{job['job_id']}"):
                            part = part_use[selected_use]
                            if part["quantity"] >= use_qty:
                                part["quantity"] -= use_qty
                                job.setdefault("actual_parts_used", []).append({
                                    "part_id": part["part_id"], "name": part["name"],
                                    "quantity": use_qty, "unit_price": part["price"],
                                    "total": use_qty * part["price"]
                                })
                                save_parts(st.session_state.parts)
                                save_job_cards(st.session_state.job_cards)
                                st.success(f"Added {use_qty} x {part['name']}")
                                st.rerun()
                            else:
                                st.error(f"Only {part['quantity']} available.")
                    if st.button(f"✔️ Complete Job", key=f"complete_{job['job_id']}"):
                        job["status"] = "Completed"
                        job["completed_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        job["mechanic_notes"] = notes
                        job["actual_labor_hours"] = actual_hours
                        save_job_cards(st.session_state.job_cards)
                        st.rerun()
                elif job["status"] == "Completed":
                    st.info("Job completed. Go to **Invoicing** to generate invoice.")
                    if st.button(f"💰 Mark as Paid (simulate)", key=f"paid_{job['job_id']}"):
                        job["status"] = "Paid"
                        save_job_cards(st.session_state.job_cards)
                        st.rerun()
                else:
                    st.success("This job is paid and closed.")
                if job.get("actual_parts_used"):
                    st.write("**Parts used:**")
                    st.dataframe(pd.DataFrame(job["actual_parts_used"])[["name", "quantity", "unit_price", "total"]], use_container_width=True)

# -------------------------------
# PARTS INVENTORY
elif menu == "🔩 Parts Inventory":
    st.markdown("<h1>🔩 Parts Inventory</h1>", unsafe_allow_html=True)
    with st.form("add_part", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Part Name *")
            sku = st.text_input("SKU")
            price = st.number_input("Unit Price ($)", min_value=0.0, step=0.5)
        with col2:
            qty = st.number_input("Initial Quantity", min_value=0, step=1)
            reorder = st.number_input("Reorder Level", min_value=0, value=5, step=1)
        if st.form_submit_button("➕ Add Part", use_container_width=True):
            if name:
                pid = get_next_id("part")
                new_part = {
                    "part_id": pid, "name": name, "sku": sku,
                    "price": price, "quantity": qty, "reorder_level": reorder
                }
                st.session_state.parts.append(new_part)
                save_parts(st.session_state.parts)
                st.success(f"Added {name}")
                st.rerun()
            else:
                st.error("Part name required.")
    if st.session_state.parts:
        df = pd.DataFrame(st.session_state.parts)
        def highlight(row):
            if row["quantity"] <= row["reorder_level"]:
                return ["background-color: #fee2e2"] * len(row)
            return [""] * len(row)
        st.dataframe(df.style.apply(highlight, axis=1), use_container_width=True)
        with st.expander("📦 Adjust Stock"):
            part_adj = st.selectbox("Select Part", [f"{p['name']} (ID: {p['part_id']})" for p in st.session_state.parts])
            delta = st.number_input("Change quantity (+/-)", step=1)
            if st.button("Apply"):
                pid = int(part_adj.split("ID: ")[1].rstrip(")"))
                for p in st.session_state.parts:
                    if p["part_id"] == pid:
                        p["quantity"] += delta
                        save_parts(st.session_state.parts)
                        st.success(f"New quantity: {p['quantity']}")
                        st.rerun()
    else:
        st.info("No parts in inventory yet.")

# -------------------------------
# INVOICING & REPORTS
elif menu == "💰 Invoicing & Reports":
    st.markdown("<h1>💰 Invoicing & Daily Reports</h1>", unsafe_allow_html=True)
    completed_jobs = [j for j in st.session_state.job_cards if j["status"] == "Completed"]
    if completed_jobs:
        with st.expander("🧾 Generate Invoice for Completed Job", expanded=True):
            job_select = {f"Job #{j['job_id']} - {j['vehicle']}": j for j in completed_jobs}
            selected = st.selectbox("Select Job", list(job_select.keys()))
            job = job_select[selected]
            parts_cost = sum(p["total"] for p in job.get("actual_parts_used", []))
            labor_cost = job.get("actual_labor_hours", 0) * 50
            subtotal = parts_cost + labor_cost
            tax = subtotal * 0.15
            total = subtotal + tax
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Parts", f"${parts_cost:.2f}")
                st.metric("Labor", f"${labor_cost:.2f}")
            with col2:
                st.metric("Subtotal", f"${subtotal:.2f}")
                st.metric("Tax (15%)", f"${tax:.2f}")
            st.metric("TOTAL", f"${total:.2f}", delta=None)
            if st.button("📄 Download Invoice PDF", use_container_width=True):
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                c.drawString(100, height-50, f"AUTOFIX PRO - INVOICE")
                c.drawString(100, height-80, f"Job #{job['job_id']} | Customer: {job['customer_name']}")
                c.drawString(100, height-100, f"Vehicle: {job['vehicle']}")
                c.drawString(100, height-120, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
                y = height-160
                c.drawString(100, y, "Parts used:")
                y -= 20
                for p in job.get("actual_parts_used", []):
                    c.drawString(120, y, f"{p['name']} x{p['quantity']} = ${p['total']:.2f}")
                    y -= 20
                c.drawString(100, y-10, f"Labor: ${labor_cost:.2f}")
                c.drawString(100, y-30, f"Tax: ${tax:.2f}")
                c.drawString(100, y-50, f"TOTAL: ${total:.2f}")
                c.showPage()
                c.save()
                buffer.seek(0)
                b64 = base64.b64encode(buffer.read()).decode()
                href = f'<a href="data:application/pdf;base64,{b64}" download="invoice_{job["job_id"]}.pdf">📥 Click to download PDF</a>'
                st.markdown(href, unsafe_allow_html=True)
            if st.button("✅ Mark as Paid", use_container_width=True):
                job["status"] = "Paid"
                save_job_cards(st.session_state.job_cards)
                st.success("Job marked as Paid.")
                st.rerun()
    else:
        st.info("No completed jobs awaiting invoicing.")
    st.markdown("---")
    st.subheader("📅 Daily Report")
    report_date = st.date_input("Select Date", date.today())
    jobs_on_date = [j for j in st.session_state.job_cards if j["created_date"].startswith(report_date.strftime("%Y-%m-%d"))]
    if jobs_on_date:
        paid = [j for j in jobs_on_date if j["status"] == "Paid"]
        revenue = 0
        for j in paid:
            parts = sum(p["total"] for p in j.get("actual_parts_used", []))
            labor = j.get("actual_labor_hours", 0) * 50
            revenue += parts + labor + (parts + labor)*0.15
        st.metric("Total Revenue (Paid Jobs)", f"${revenue:.2f}")
        st.write(f"Jobs created: {len(jobs_on_date)} | Paid: {len(paid)}")
        st.dataframe(pd.DataFrame(jobs_on_date)[["job_id", "vehicle", "status"]], use_container_width=True)
    else:
        st.info("No jobs on that date.")
