from flask import Blueprint, render_template
import os
from modules.utils import role_required

def get_employee_status(emp_df, leave_df=None):
    import pandas as pd

    today = pd.Timestamp.now().normalize()

    # -----------------------------
    # Prepare Leave Data
    # -----------------------------
    if leave_df is None or leave_df.empty:
        leave_df = pd.DataFrame(columns=['Employee ID', 'Start Date', 'End Date', 'Status'])
    else:
        leave_df = leave_df.copy()
        leave_df.columns = leave_df.columns.str.strip()

        leave_df['Employee ID'] = leave_df['Employee ID'].astype(str)
        leave_df['Start Date'] = pd.to_datetime(leave_df['Start Date'], errors='coerce')
        leave_df['End Date'] = pd.to_datetime(leave_df['End Date'], errors='coerce')

        # Normalize status text
        leave_df['Status'] = leave_df['Status'].astype(str).str.strip().str.lower()

    # -----------------------------
    # Prepare Employee Data
    # -----------------------------
    emp_df = emp_df.copy()

    emp_df['Employee ID'] = emp_df['Employee ID'].astype(str)
    emp_df['Status'] = emp_df['Status'].fillna('Active').astype(str).str.strip().str.lower()

    current_status = []

    # -----------------------------
    # Compute Current Status
    # -----------------------------
    for _, emp in emp_df.iterrows():

        emp_id = emp['Employee ID']
        emp_status = emp['Status']

        if emp_status == 'suspended':
            status = 'Suspended'

        elif emp_status == 'inactive':
            status = 'Inactive'

        else:
            on_leave = leave_df[
                (leave_df['Employee ID'] == emp_id) &
                (leave_df['Status'].str.contains('approved')) &
                (leave_df['Start Date'] <= today) &
                (leave_df['End Date'] >= today)
            ]

            if not on_leave.empty:
                status = 'On Leave'
            else:
                status = 'Active'

        current_status.append(status)

    emp_df['Current Status'] = current_status

    return emp_df


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')  # or the correct path to your data files

hr_bp = Blueprint('hr', __name__, url_prefix='/hr')

@hr_bp.route('/')
def hr_home():
    return render_template('hr/home.html')


import pandas as pd
import os
from flask import request, redirect, url_for, flash

DATA_FOLDER = 'data'
EMPLOYEE_FILE = os.path.join(DATA_FOLDER, 'employees.xlsx')

def read_employees():
    if os.path.exists(EMPLOYEE_FILE):
        return pd.read_excel(EMPLOYEE_FILE)
    return pd.DataFrame(columns=["Employee ID", "Full Name", "Position", "Department", "Date Hired", "Contact", "Status", "Grade", "National ID", "Village", "TA", "District", "Date of Birth", "Spouse", "Children", "Season", "BANK ACC"])

def save_employees(df):
    df.to_excel(EMPLOYEE_FILE, index=False)

@hr_bp.route('/employees')
def list_employees():
    import pandas as pd

    emp_df = pd.read_excel(EMPLOYEE_FILE)
    emp_df.columns = emp_df.columns.str.strip()

    leave_df = pd.read_excel(LEAVE_FILE) if os.path.exists(LEAVE_FILE) else None

    emp_df = get_employee_status(emp_df, leave_df)
    employees = emp_df.to_dict(orient='records')
    return render_template('hr/employee_list.html', employees=employees)


@hr_bp.route('/employees/add', methods=['GET', 'POST'])
@role_required(['HR Supervisor', 'HR Officer', 'Admin'])
def add_employee():
    if request.method == 'POST':
        df = read_employees()

        new_data = {
            "Employee ID": request.form.get('employee_id'),
            "Full Name": request.form.get('full_name'),
            "Position": request.form.get('position'),
            "Department": request.form.get('department'),
            "Section": request.form.get('section'),
            "Date Hired": request.form.get('date_hired'),
            "Contact": request.form.get('contact'),
            "Status": request.form.get('status'),
            "Grade": request.form.get('grade'),
            "National ID": request.form.get('national_id'),
            "Village": request.form.get('village'),
            "TA": request.form.get('ta'),              # FIXED
            "District": request.form.get('district'),
            "Date of Birth": request.form.get('date_of_birth'),
            "Spouse": request.form.get('spouse'),
            "Children": request.form.get('children'),  # FIXED
            "Season": request.form.get('season'),      # FIXED
            "BANK ACC": request.form.get('bank_acc')
        }

        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        save_employees(df)

        return redirect(url_for('hr.list_employees'))

    return render_template(
        'hr/employee_form.html',
        action='Add',
        employee={}
    )

@hr_bp.route('/edit_employee/<emp_id>', methods=['GET', 'POST'])
def edit_employee(emp_id):
    if not os.path.exists(EMPLOYEE_FILE):
        return "Employee file not found."

    df = pd.read_excel(EMPLOYEE_FILE)

    if request.method == 'POST':
        full_name = request.form['full_name']
        position = request.form['position']
        department = request.form['department']
        date_hired = request.form['date_hired']
        contact = request.form['contact']
        status = request.form['status']

        # Ensure emp_id matches a row
        if emp_id in df['Employee ID'].astype(str).values:
            df.loc[df['Employee ID'].astype(str) == emp_id, 'Full Name'] = full_name
            df.loc[df['Employee ID'].astype(str) == emp_id, 'Position'] = position
            df.loc[df['Employee ID'].astype(str) == emp_id, 'Department'] = department
            df.loc[df['Employee ID'].astype(str) == emp_id, 'Date Hired'] = date_hired
            df.loc[df['Employee ID'].astype(str) == emp_id, 'Contact'] = contact
            df.loc[df['Employee ID'].astype(str) == emp_id, 'Status'] = status

            df.to_excel(EMPLOYEE_FILE, index=False)
            flash('Employee updated successfully.', 'success')
            return redirect(url_for('hr.list_employees'))
        else:
            flash('Employee ID not found.', 'danger')

    # Pre-fill form for GET
    emp_record = df[df['Employee ID'].astype(str) == emp_id].to_dict('records')
    if not emp_record:
        return f"No employee found with ID {emp_id}"
    return render_template('hr/employee_form.html', employee=emp_record[0])

@hr_bp.route('/employees/delete/<emp_id>')
@role_required(['HR Supervisor', 'HR Officer', 'Admin'])
def delete_employee(emp_id):
    df = read_employees()
    df = df[df['Employee ID'] != emp_id]
    save_employees(df)
    return redirect(url_for('hr.list_employees'))


import pandas as pd
from flask import jsonify, render_template, request, redirect, url_for, flash
import os

EMPLOYEE_FILE = os.path.join(DATA_DIR, 'employees.xlsx')
LEAVE_FILE = os.path.join(DATA_DIR, 'leave_records.xlsx')
ATTENDANCE_FILE = os.path.join(DATA_DIR, 'attendance.xlsx')


def load_employee_dict_with_status():
    """
    Return a dictionary of all employees with their current status:
    'Active', 'On Leave', 'Suspended' with emoji symbols.
    """
    if not os.path.exists(EMPLOYEE_FILE):
        return {}

    df = pd.read_excel(EMPLOYEE_FILE)
    df.columns = df.columns.str.strip()
    df["Employee ID"] = df["Employee ID"].astype(str)
    today = pd.Timestamp.now().normalize()

    # Prepare leave info
    leave_dict = {}
    if os.path.exists(LEAVE_FILE):
        leave_df = pd.read_excel(LEAVE_FILE)
        leave_df.columns = leave_df.columns.str.strip()
        leave_df['Employee ID'] = leave_df['Employee ID'].astype(str)
        leave_df['Start Date'] = pd.to_datetime(leave_df['Start Date'], errors='coerce')
        leave_df['End Date'] = pd.to_datetime(leave_df['End Date'], errors='coerce')

        # Only consider approved leaves that include today
        current_leave = leave_df[
            (leave_df['Status'].str.lower() == 'approved') &
            (leave_df['Start Date'] <= today) &
            (leave_df['End Date'] >= today)
        ]
        leave_dict = dict(zip(current_leave['Employee ID'], current_leave['Employee Name']))

    emp_dict = {}
    for _, row in df.iterrows():
        emp_id = str(row['Employee ID'])
        status = str(row.get('Status', '')).strip().lower()

        if status == 'suspended':
            display_status = "🔴 Suspended"
        elif emp_id in leave_dict:
            display_status = "🟡 On Leave"
        elif status == 'active':
            display_status = "🟢 Active"
        else:
            display_status = status.capitalize() if status else "Unknown"

        emp_dict[emp_id] = f"{row['Full Name']} ({display_status})"

    return emp_dict


@hr_bp.route('/attendance', methods=['GET', 'POST'])
def attendance_tracking():
    emp_dict = load_employee_dict_with_status()

    if request.method == 'POST':
        form_data = request.form.to_dict()
        records = []
        i = 1
        while f'emp_number_{i}' in form_data:
            emp_number = form_data.get(f'emp_number_{i}', '').strip()
            if not emp_number:
                i += 1
                continue

            # Extract the name without emoji/status for storage
            full_name = emp_dict.get(emp_number, '')
            name_only = full_name.split(' (')[0] if full_name else ''

            row = {
                'Date': form_data.get(f'date_{i}', ''),
                'Employee Number': emp_number,
                'Employee Name': name_only,
                'Basic Earnings': form_data.get(f'basic_{i}', 0),
                'Overtime': form_data.get(f'overtime_{i}', 0),
                'Tons Cut': form_data.get(f'tons_{i}', 0),
                'Farm Number': form_data.get(f'farm_{i}', ''),
                'Activity/Remarks': form_data.get(f'activity_{i}', ''),
                'Supervisor': form_data.get(f'supervisor_{i}', ''),
                'Location': form_data.get(f'location_{i}', '')
            }
            records.append(row)
            i += 1

        df = pd.DataFrame(records)
        if os.path.exists(ATTENDANCE_FILE):
            df_existing = pd.read_excel(ATTENDANCE_FILE)
            df = pd.concat([df_existing, df], ignore_index=True)

        df.to_excel(ATTENDANCE_FILE, index=False)
        flash(f"{len(records)} attendance record(s) saved successfully!", "success")
        return redirect(url_for('hr.attendance_tracking'))

    return render_template('hr/attendance.html', emp_dict=emp_dict)


@hr_bp.route('/get_emp_name/<emp_id>')
def get_emp_name(emp_id):
    emp_dict = load_employee_dict_with_status()
    name = emp_dict.get(emp_id.strip(), '')
    name_only = name.split(' (')[0] if name else ''
    return jsonify({'name': name_only})


EMPLOYEE_FILE = 'data/employee.xlsx'

@hr_bp.route('/generate_payroll', methods=['GET', 'POST'])
def generate_payroll():
    attendance_file = os.path.join(DATA_DIR, 'attendance.xlsx')
    if not os.path.exists(attendance_file):
        flash("Attendance data not found.", "danger")
        return redirect(url_for('hr.hr_home'))

    df = pd.read_excel(attendance_file)
    df['Date'] = pd.to_datetime(df['Date'])

    emp_payroll = []

    if request.method == 'POST':
        start_date = pd.to_datetime(request.form.get('start_date'))
        end_date = pd.to_datetime(request.form.get('end_date'))
        overtime_rate = float(request.form.get('overtime_rate', 150))  # per hour

        # Filter by period
        period_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

        if period_df.empty:
            flash("No attendance records in selected period.", "warning")
        else:
            grouped = period_df.groupby(['Employee Number', 'Employee Name'])

            for (emp_id, name), group in grouped:
                basic_total = group['Basic Earnings'].sum()
                overtime_total = group['Overtime'].sum()
                ot_pay = overtime_total * overtime_rate
                net_pay = basic_total + ot_pay

                emp_payroll.append({
                    "Employee ID": emp_id,
                    "Name": name,
                    "Start": start_date.date(),
                    "End": end_date.date(),
                    "Basic": round(basic_total, 2),
                    "Overtime": round(overtime_total, 2),
                    "OT Pay": round(ot_pay, 2),
                    "Net Pay": round(net_pay, 2)
                })

            # Optionally save to payroll.xlsx
            save_path = os.path.join(DATA_DIR, 'payroll.xlsx')
            pd.DataFrame(emp_payroll).to_excel(save_path, index=False)
            flash(f"Payroll generated and saved to 'payroll.xlsx'.", "success")

    return render_template("hr/generate_payroll.html", results=emp_payroll)


import os
import pandas as pd
from flask import request, render_template


DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
PAYROLL_FILE = os.path.join(DATA_DIR, 'payroll.xlsx')
EMPLOYEE_FILE = os.path.join(DATA_DIR, 'employees.xlsx')  # make sure this exists

@hr_bp.route('/payroll_report', methods=['GET', 'POST'])
def payroll_report():
    df = pd.read_excel(PAYROLL_FILE) if os.path.exists(PAYROLL_FILE) else pd.DataFrame()
    results = []
    filters = {
        'emp_id': '',
        'start_date': '',
        'end_date': ''
    }

    if not df.empty:
        df['Start'] = pd.to_datetime(df['Start'], errors='coerce')
        df['End'] = pd.to_datetime(df['End'], errors='coerce')
        df['Employee ID'] = df['Employee ID'].astype(str)

    if request.method == 'POST':
        emp_id = request.form.get('emp_id')
        start = request.form.get('start_date')
        end = request.form.get('end_date')
        filters.update({'emp_id': emp_id, 'start_date': start, 'end_date': end})

        if emp_id:
            df = df[df['Employee ID'] == emp_id]
        if start:
            df = df[df['Start'] >= pd.to_datetime(start)]
        if end:
            df = df[df['End'] <= pd.to_datetime(end)]

        results = df.to_dict('records')

    emp_df = pd.read_excel(EMPLOYEE_FILE) if os.path.exists(EMPLOYEE_FILE) else pd.DataFrame()
    emp_df = emp_df.dropna(subset=['Employee ID', 'Full Name'])
    emp_df['Employee ID'] = emp_df['Employee ID'].astype(str)
    emp_df['Full Name'] = emp_df['Full Name'].astype(str)
    emp_options = sorted(emp_df[['Employee ID', 'Full Name']].values.tolist(), key=lambda x: (x[1], x[0]))

    return render_template('hr/payroll_report.html', records=results, emp_options=emp_options, filters=filters)



ATTENDANCE_FILE = os.path.join(DATA_DIR, 'attendance.xlsx')

@hr_bp.route('/attendance_report', methods=['GET', 'POST'])
def attendance_report():

    df = pd.read_excel(ATTENDANCE_FILE) if os.path.exists(ATTENDANCE_FILE) else pd.DataFrame()

    results = []

    filters = {
        'emp_id': '',
        'start_date': '',
        'end_date': ''
    }

    summary = {
        "days": 0,
        "basic": 0,
        "ot": 0,
        "tons": 0
    }

    if request.method == 'POST':

        emp_id = request.form.get('emp_id','').strip()
        start = request.form.get('start_date')
        end = request.form.get('end_date')

        filters.update({'emp_id': emp_id, 'start_date': start, 'end_date': end})

        if not df.empty:

            df.columns = df.columns.str.strip()

            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

            # Ensure numeric columns
            for col in ['Basic Earnings','Overtime','Tons Cut']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # Filtering
            if emp_id:
                df = df[df['Employee Number'].astype(str) == emp_id]

            if start:
                df = df[df['Date'] >= pd.to_datetime(start)]

            if end:
                df = df[df['Date'] <= pd.to_datetime(end)]

            results = df.to_dict('records')

            # ---- CALCULATE SUMMARY ----
            summary["days"] = len(df)
            summary["basic"] = df['Basic Earnings'].sum()
            summary["ot"] = df['Overtime'].sum()
            summary["tons"] = df['Tons Cut'].sum()

    return render_template(
        'hr/attendance_report.html',
        records=results,
        filters=filters,
        summary=summary
    )

import pandas as pd
from flask import request, render_template, redirect, url_for, flash
import os
from datetime import datetime

EMPLOYEE_FILE = os.path.join(DATA_DIR, 'employees.xlsx')
LEAVE_FILE = os.path.join(DATA_DIR, 'leave_records.xlsx')
GRADE_RULES_FILE = os.path.join(DATA_DIR, 'grade_rules.xlsx')
@hr_bp.route('/apply_leave', methods=['GET', 'POST'])
def apply_leave():
    import pandas as pd
    import os

    # Safe loader for Excel files
    def safe_read_excel(filepath, default_cols):
        if os.path.exists(filepath):
            df = pd.read_excel(filepath)
            df.columns = df.columns.map(str).str.strip()
        else:
            df = pd.DataFrame(columns=default_cols)
        return df

    # Define expected columns
    emp_cols = ['Employee ID', 'Full Name', 'Grade']
    grade_cols = ['Grade', 'Annual Leave', 'Sick Leave', 'Maternity Leave', 'Compassionate Leave']
    leave_cols = ['Employee ID', 'Employee Name', 'Leave Type', 'Start Date', 'End Date', 'Total Days', 'Reason', 'Status', 'Remarks']

    # Load data
    emp_df = safe_read_excel(EMPLOYEE_FILE, emp_cols)
    grade_rules_df = safe_read_excel(GRADE_RULES_FILE, grade_cols)
    leave_df = safe_read_excel(LEAVE_FILE, leave_cols)

    emp_df = emp_df.dropna(subset=['Employee ID', 'Full Name'])
    emp_options = emp_df[emp_cols].dropna().values.tolist()

    # Map Excel column to internal leave types
    column_to_leave_type = {
        'Annual Leave': 'Annual',
        'Sick Leave': 'Sick',
        'Maternity Leave': 'Maternity',
        'Compassionate Leave': 'Compassionate'
    }

    # Compute leave balances
    leave_balances = {}
    for _, row in emp_df.iterrows():
        emp_id = row['Employee ID']
        grade = row.get('Grade', '')
        balances = {}

        if not grade_rules_df.empty and grade:
            rules = grade_rules_df[grade_rules_df['Grade'] == grade]
            if not rules.empty:
                for col, leave_type in column_to_leave_type.items():
                    if col in rules.columns:
                        allocated = rules.iloc[0][col]
                        used = leave_df[
                            (leave_df['Employee ID'] == emp_id) &
                            (leave_df['Leave Type'] == leave_type) &
                            (leave_df['Status'].isin(['Approved', 'Pending']))
                        ]['Total Days'].sum()
                        balances[leave_type] = max(0, allocated - used)

                balances['Unpaid'] = 999  # Allow unlimited unpaid leave
        leave_balances[emp_id] = balances

    # Handle form submission
    if request.method == 'POST':
        emp_id = request.form.get('emp_id')
        name = request.form.get('name')
        leave_type = request.form.get('leave_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        reason = request.form.get('reason')

        try:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            total_days = (end_dt - start_dt).days + 1
        except Exception:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for('hr.apply_leave'))

        new_entry = {
            'Employee ID': emp_id,
            'Employee Name': name,
            'Leave Type': leave_type,
            'Start Date': start_dt,
            'End Date': end_dt,
            'Total Days': total_days,
            'Reason': reason,
            'Status': 'Pending',
            'Remarks': ''
        }

        df = safe_read_excel(LEAVE_FILE, leave_cols)
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_excel(LEAVE_FILE, index=False)

        flash("Leave application submitted successfully.", "success")
        return redirect(url_for('hr.apply_leave'))
    import numpy as np

    # Safely convert all NumPy types to native Python types
    leave_balances = {
        emp_id: {lt: val.item() if isinstance(val, np.generic) else val for lt, val in leaves.items()}
        for emp_id, leaves in leave_balances.items()
    }

    return render_template('hr/apply_leave.html', emp_options=emp_options, leave_balances=leave_balances)


from flask import request, render_template, redirect, url_for
import pandas as pd
import os

@hr_bp.route('/leave_approvals', methods=['GET', 'POST'])
@role_required(['agriculture Manager', 'Manager', 'HR Officer', 'Admin'])
def leave_approvals():
    if os.path.exists(LEAVE_FILE):
        df = pd.read_excel(LEAVE_FILE)
    else:
        df = pd.DataFrame()

    if request.method == 'POST':
        index = int(request.form['row_index'])
        decision = request.form['decision']
        approver = request.form['approver']
        remarks = request.form['remarks']

        if 0 <= index < len(df):
            df.at[index, 'Status'] = decision
            df.at[index, 'Approver'] = approver
            df.at[index, 'Remarks'] = remarks
            df.to_excel(LEAVE_FILE, index=False)

        return redirect(url_for('hr.leave_approvals'))

    pending_df = df[df['Status'] == 'Pending'] if not df.empty else pd.DataFrame()
    records = pending_df.reset_index().to_dict('records')  # includes original index
    return render_template('hr/leave_approvals.html', records=records)

@hr_bp.route('/check_leave_status', methods=['GET', 'POST'])
def check_leave_status():
    records = []
    if request.method == 'POST':
        name_or_id = request.form['name_or_id']
        file_path = os.path.join(DATA_DIR, 'leave_records.xlsx')
        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
            df_filtered = df[
                df['Employee Name'].str.contains(name_or_id, case=False, na=False) |
                df['Employee ID'].astype(str).str.contains(name_or_id, na=False)
            ]
            records = df_filtered.to_dict(orient='records')
    return render_template('hr/check_leave_status.html', records=records)

@hr_bp.route('/assign_task', methods=['GET', 'POST'])
@role_required(['agriculture Manager', 'Manager', 'HR Officer' , 'Admin'])
def assign_task():
    task_file = os.path.join(DATA_DIR, 'task_assignments.xlsx')

    if request.method == 'POST':
        date = request.form['date']
        employee_id = request.form['employee_id']
        task_description = request.form['task_description']
        deadline = request.form['deadline']
        assigned_by = request.form['assigned_by']
        status = 'Pending'

        new_task = pd.DataFrame([{
            'Date': date,
            'Employee ID': employee_id,
            'Task Description': task_description,
            'Deadline': deadline,
            'Assigned By': assigned_by,
            'Status': status
        }])

        if os.path.exists(task_file):
            existing = pd.read_excel(task_file)
            df = pd.concat([existing, new_task], ignore_index=True)
        else:
            df = new_task

        df.to_excel(task_file, index=False)
        flash('Task assigned successfully!', 'success')
        return redirect(url_for('hr.assign_task'))

    return render_template('hr/assign_task.html')


@hr_bp.route('/hr/reports')
def hr_reports():

    summary = {
        "employees": {"total":0,"active":0,"leave":0,"suspended":0},
        "attendance": {"days":0,"basic":0,"overtime":0,"tons":0},
        "cutters": {"total":0,"avg":0,"top_name":"N/A","top_tons":0},
        "leave": {"total":0,"approved":0,"pending":0},
        "performance": {"total_records":0}
    }

    sparkline_data = {
        "employees": {"labels": [], "data": []},
        "attendance": {"labels": [], "data": []},
        "cutting": {"labels": [], "data": []},
        "cutters": {"labels": [], "data": []},
        "leave": {"labels": [], "data": []},
        "performance": {"labels": [], "data": []},
    }

    attendance_chart = {"labels": [], "datasets": [{"label":"Earnings", "data": []}]}
    leave_chart = {"labels": [], "datasets": [{"data": []}]}
    cutters_chart = {"labels": [], "datasets":[{"label":"Tons Cut","data":[],"backgroundColor":"#e74a3b"}]}

    department_chart = {
        "labels": [],
        "datasets": [{
            "label": "Employees",
            "data": [],
            "backgroundColor": "#4e73df"
        }]
    }

    productivity_chart = {
        "labels": [],
        "datasets": [{
            "label": "Tons per Worker",
            "data": [],
            "borderColor": "#198754",
            "backgroundColor": "rgba(25,135,84,0.2)",
            "fill": True,
            "tension": 0.4
        }]
    }

    cutters = pd.DataFrame()
    att_df = pd.DataFrame()

    try:

        # ---------------- Employees ----------------
        emp_file = os.path.join(DATA_DIR,'employees.xlsx')

        if os.path.exists(emp_file):

            emp_df = pd.read_excel(emp_file)
            emp_df.columns = emp_df.columns.str.strip()

            summary["employees"]["total"] = len(emp_df)

            if "Current Status" in emp_df.columns:

                summary["employees"]["active"] = len(emp_df[emp_df["Current Status"].str.strip()=="Active"])
                summary["employees"]["leave"] = len(emp_df[emp_df["Current Status"].str.strip()=="On Leave"])
                summary["employees"]["suspended"] = len(emp_df[emp_df["Current Status"].str.strip()=="Suspended"])

            sparkline_data["employees"]["labels"] = list(range(1,7))
            sparkline_data["employees"]["data"] = list(range(len(emp_df)))[:6]

            # Department breakdown
            if "Department" in emp_df.columns:

                dept_counts = emp_df["Department"].value_counts()

                department_chart["labels"] = dept_counts.index.tolist()
                department_chart["datasets"][0]["data"] = dept_counts.values.tolist()

            # Section breakdown per department
            department_sections = {}

            if "Department" in emp_df.columns and "Section" in emp_df.columns:

                grouped = emp_df.groupby(["Department", "Section"]).size().reset_index(name="Count")

                for _, row in grouped.iterrows():

                    dept = row["Department"]
                    section = row["Section"]
                    count = int(row["Count"])

                    if dept not in department_sections:
                        department_sections[dept] = {
                            "labels": [],
                            "data": []
                        }

                    department_sections[dept]["labels"].append(section)
                    department_sections[dept]["data"].append(count)

        # ---------------- Attendance ----------------
        att_file = os.path.join(DATA_DIR,'attendance.xlsx')

        if os.path.exists(att_file):

            att_df = pd.read_excel(att_file)
            att_df.columns = att_df.columns.str.strip()

            summary["attendance"]["days"] = len(att_df)

            att_df["Basic Earnings"] = pd.to_numeric(att_df.get("Basic Earnings",0),errors="coerce").fillna(0)
            att_df["Overtime"] = pd.to_numeric(att_df.get("Overtime",0),errors="coerce").fillna(0)
            att_df["Tons Cut"] = pd.to_numeric(att_df.get("Tons Cut",0),errors="coerce").fillna(0)

            summary["attendance"]["basic"] = round(att_df["Basic Earnings"].sum(),2)
            summary["attendance"]["overtime"] = round(att_df["Overtime"].sum(),2)
            summary["attendance"]["tons"] = round(att_df["Tons Cut"].sum(),2)

            sparkline_data["attendance"]["labels"] = list(range(1,7))
            sparkline_data["attendance"]["data"] = att_df["Basic Earnings"].head(6).tolist()

            attendance_chart["labels"] = att_df.index.astype(str).tolist()[:10]
            attendance_chart["datasets"][0]["data"] = (
                att_df["Basic Earnings"] + att_df["Overtime"]
            ).head(10).tolist()

            # Cutter performance
            cutters = att_df[att_df["Tons Cut"] > 0]

            if not cutters.empty:

                summary["cutters"]["total"] = len(cutters)
                summary["cutters"]["avg"] = round(cutters["Tons Cut"].mean(), 2)

                top = cutters.loc[cutters["Tons Cut"].idxmax()]
                summary["cutters"]["top_name"] = top.get("Employee Name","N/A")
                summary["cutters"]["top_tons"] = round(top["Tons Cut"],2)

                sparkline_data["cutting"]["labels"] = list(range(1,7))
                sparkline_data["cutting"]["data"] = cutters["Tons Cut"].head(6).tolist()

                cutters_chart["labels"] = cutters["Employee Name"].head(10).tolist()
                cutters_chart["datasets"][0]["data"] = cutters["Tons Cut"].head(10).tolist()

                # Productivity chart
                if "Date" in cutters.columns:

                    cutters["Date"] = pd.to_datetime(cutters["Date"],errors="coerce")

                    cutters["Month"] = cutters["Date"].dt.strftime("%b")

                    monthly = cutters.groupby("Month")["Tons Cut"].sum().reset_index()

                    productivity_chart["labels"] = monthly["Month"].tolist()
                    productivity_chart["datasets"][0]["data"] = monthly["Tons Cut"].tolist()


        # ---------------- Leave ----------------
        leave_file = os.path.join(DATA_DIR,'leave_records.xlsx')

        if os.path.exists(leave_file):

            leave_df = pd.read_excel(leave_file)
            leave_df.columns = leave_df.columns.str.strip()

            summary["leave"]["total"] = len(leave_df)
            summary["leave"]["approved"] = len(leave_df[leave_df.get("Status","")=="Approved"])
            summary["leave"]["pending"] = len(leave_df[leave_df.get("Status","")=="Pending"])

            sparkline_data["leave"]["labels"] = list(range(1,7))
            sparkline_data["leave"]["data"] = [
                summary["leave"]["approved"],
                summary["leave"]["pending"],
                0,0,0,0
            ]

            leave_chart["labels"] = ["Approved","Pending"]
            leave_chart["datasets"][0]["data"] = [
                summary["leave"]["approved"],
                summary["leave"]["pending"]
            ]


        # ---------------- Performance ----------------
        perf_file = os.path.join(DATA_DIR,'employee_performance.xlsx')

        if os.path.exists(perf_file):

            perf_df = pd.read_excel(perf_file)

            summary["performance"]["total_records"] = len(perf_df)

            sparkline_data["performance"]["labels"] = list(range(1,7))
            sparkline_data["performance"]["data"] = list(range(len(perf_df)))[:6]


        # ---------------- Insights ----------------

        top_cutters = []

        if not cutters.empty:

            top_df = cutters.sort_values("Tons Cut",ascending=False).head(20)

            for _,row in top_df.iterrows():

                top_cutters.append({
                    "name": row.get("Employee Name","N/A"),
                    "tons": round(row.get("Tons Cut",0),2)
                })


        low_attendance = []

        if not att_df.empty and "Employee Name" in att_df.columns:

            low_df = att_df.groupby("Employee Name").size().reset_index(name="Days")

            low_df = low_df.sort_values("Days").head(5)

            for _,row in low_df.iterrows():

                low_attendance.append({
                    "name": row["Employee Name"],
                    "days": int(row["Days"])
                })

    except Exception as e:
        print("HR Report Error:", e)


    return render_template(
        "hr/hr_reports.html",
        summary=summary,
        sparkline_data=sparkline_data,
        attendance_chart=attendance_chart,
        department_chart=department_chart,
        department_sections=department_sections,
        leave_chart=leave_chart,
        cutters_chart=cutters_chart,
        top_cutters=top_cutters,
        low_attendance=low_attendance,
        productivity_chart=productivity_chart
    )


# Route: HR Grade & Leave Configuration
@hr_bp.route('/hr/config', methods=['GET', 'POST'])
@role_required(['HR Supervisor', 'HR Officer', 'Admin'])
def hr_config():
    config_file = os.path.join(DATA_DIR, 'pay_rules.xlsx')

    # If form submitted
    if request.method == 'POST':
        grades = request.form.getlist('grade')
        basic_rates = request.form.getlist('basic_rate')
        overtime_rates = request.form.getlist('overtime_rate')
        nhif = request.form.getlist('nhif')
        nssf = request.form.getlist('nssf')
        annual = request.form.getlist('annual_leave')
        sick = request.form.getlist('sick_leave')
        maternity = request.form.getlist('maternity_leave')
        deductions = request.form.getlist('deductions')

        data = []
        for i in range(len(grades)):
            data.append({
                'Grade': grades[i],
                'Basic Rate (per day)': basic_rates[i],
                'Overtime Rate (per hour)': overtime_rates[i],
                'NHIF (%)': nhif[i],
                'NSSF (%)': nssf[i],
                'Annual Leave (days)': annual[i],
                'Sick Leave (days)': sick[i],
                'Maternity Leave (days)': maternity[i],
                'Other Deductions': deductions[i],
            })

        df = pd.DataFrame(data)
        df.to_excel(config_file, index=False)
        flash('Configuration updated successfully!', 'success')
        return redirect(url_for('hr.hr_config'))

    # On GET, load config
    if os.path.exists(config_file):
        df = pd.read_excel(config_file)
    else:
        df = pd.DataFrame(columns=[
            'Grade', 'Basic Rate (per day)', 'Overtime Rate (per hour)', 'NHIF (%)', 'NSSF (%)',
            'Annual Leave (days)', 'Sick Leave (days)', 'Maternity Leave (days)', 'Other Deductions'])

    return render_template('hr/hr_config.html', df=df)


@hr_bp.route('/grade_config', methods=['GET', 'POST'])
@role_required(['HR Supervisor', 'HR Officer', 'Admin'])
def grade_config():
    file_path = os.path.join(DATA_DIR, 'grade_rules.xlsx')
    columns = ['Grade', 'Daily Rate', 'Annual Leave', 'Sick Leave', 'Maternity Leave', 'Compassionate Leave']

    if request.method == 'POST':
        # Get form data
        new_data = {
            'Grade': request.form['grade'],
            'Daily Rate': float(request.form['daily_rate']),
            'Annual Leave': int(request.form['annual_leave']),
            'Sick Leave': int(request.form['sick_leave']),
            'Maternity Leave': int(request.form['maternity_leave']),
            'Compassionate Leave': int(request.form['compassionate_leave']),
        }

        # Load or create DataFrame
        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
        else:
            df = pd.DataFrame(columns=columns)

        # Update or insert
        df = df[df['Grade'] != new_data['Grade']]
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        df.to_excel(file_path, index=False)

        flash('Grade configuration saved successfully!', 'success')
        return redirect(url_for('hr.grade_config'))

    # Load existing grades
    df = pd.read_excel(file_path) if os.path.exists(file_path) else pd.DataFrame(columns=columns)
    return render_template('hr/grade_config.html', grades=df.to_dict(orient='records'))

from flask import Blueprint, render_template, request, flash
import pandas as pd
import os
from datetime import datetime

PHOTO_FOLDER = "static/employee_photos"

def calculate_retirement(dob):
    try:
        dob = pd.to_datetime(dob)
        retirement_date = dob.replace(year=dob.year + 60)
        years_left = (retirement_date - pd.Timestamp.now()).days // 365
        return f"{years_left} years left ({retirement_date.date()})"
    except:
        return "Unknown"


@hr_bp.route('/employee_profile')
def employee_profile():
    import pandas as pd
    import os

    # -----------------------------
    # Check Employee File
    # -----------------------------
    if not os.path.exists(EMPLOYEE_FILE):
        flash("Employee data file not found!", "danger")
        return render_template('hr/employee_profile.html', selected_employee=None)

    # -----------------------------
    # Load Employees
    # -----------------------------
    df = pd.read_excel(EMPLOYEE_FILE)
    df.columns = df.columns.str.strip()
    df["Employee ID"] = df["Employee ID"].astype(str)

    emp_id = request.args.get("emp_id")

    if emp_id not in df["Employee ID"].values:
        flash(f"No employee found with ID {emp_id}", "warning")
        return render_template('hr/employee_profile.html', selected_employee=None)

    selected_employee = df[df["Employee ID"] == emp_id].iloc[0]

    # -----------------------------
    # Retirement Info
    # -----------------------------
    retirement_info = ""
    near_retirement = False

    try:
        dob = pd.to_datetime(selected_employee.get("Date of Birth"))
        retirement_date = dob.replace(year=dob.year + 60)

        years_left = (retirement_date - pd.Timestamp.now()).days // 365
        retirement_info = f"{years_left} years left ({retirement_date.date()})"

        near_retirement = years_left <= 2
    except:
        retirement_info = "Unknown"

    # -----------------------------
    # Photo
    # -----------------------------
    photo = None
    photo_path = os.path.join(PHOTO_FOLDER, f"{emp_id}.jpg")
    if os.path.exists(photo_path):
        photo = f"{emp_id}.jpg"

    # -----------------------------
    # Helper function to load Excel from data folder
    # -----------------------------
    def load_filtered_by_id(file_name, id_column='Employee ID'):
        path = os.path.join('data', file_name)

        try:
            df_file = pd.read_excel(path)
            df_file.columns = df_file.columns.str.strip()
            df_file[id_column] = df_file[id_column].astype(str)

            return df_file[df_file[id_column] == emp_id]

        except:
            return pd.DataFrame()

    # -----------------------------
    # Load Employee Records
    # -----------------------------
    promotions = load_filtered_by_id("promotions.xlsx")
    discipline = load_filtered_by_id("discipline.xlsx")
    training = load_filtered_by_id("training.xlsx")
    appraisals = load_filtered_by_id("appraisals.xlsx")

    # -----------------------------
    # Load Leaves & Compute Current Status
    # -----------------------------
    try:
        leaves_path = os.path.join('data', "leave_records.xlsx")

        leaves_df = pd.read_excel(leaves_path)
        leaves_df.columns = leaves_df.columns.str.strip()

        leaves_df['Employee ID'] = leaves_df['Employee ID'].astype(str)
        leaves_df['Start Date'] = pd.to_datetime(leaves_df['Start Date'], errors='coerce')
        leaves_df['End Date'] = pd.to_datetime(leaves_df['End Date'], errors='coerce')

        leaves = leaves_df[leaves_df['Employee ID'] == emp_id]

        today = pd.Timestamp.now().normalize()

        # Base status from employee record
        emp_status = str(selected_employee.get('Status', '')).strip().lower()

        # Detect active approved leave
        on_leave = leaves[
            (leaves['Status'].astype(str).str.strip().str.lower().str.contains('approved')) &
            (leaves['Start Date'] <= today) &
            (leaves['End Date'] >= today)
        ]

        # Determine Current Status
        if emp_status == 'suspended':
            selected_employee['Current Status'] = 'Suspended'

        elif emp_status == 'inactive':
            selected_employee['Current Status'] = 'Inactive'

        elif not on_leave.empty:
            selected_employee['Current Status'] = 'On Leave'

        else:
            selected_employee['Current Status'] = 'Active'

    except Exception as e:
        print("Leave loading error:", e)

        leaves = pd.DataFrame()
        selected_employee['Current Status'] = selected_employee.get('Status', 'Active')

    # -----------------------------
    # Render Template
    # -----------------------------
    return render_template(
        'hr/employee_profile.html',
        selected_employee=selected_employee,
        retirement_info=retirement_info,
        near_retirement=near_retirement,
        photo=photo,
        promotions=promotions,
        discipline=discipline,
        training=training,
        appraisals=appraisals,
        leaves=leaves
    )