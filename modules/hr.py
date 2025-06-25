from flask import Blueprint, render_template
import os
from modules.utils import role_required

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
    return pd.DataFrame(columns=["Employee ID", "Full Name", "Position", "Department", "Date Hired", "Contact", "Status"])

def save_employees(df):
    df.to_excel(EMPLOYEE_FILE, index=False)

@hr_bp.route('/employees')
def list_employees():
    employees = read_employees().to_dict('records')
    return render_template('hr/employee_list.html', employees=employees)

@hr_bp.route('/employees/add', methods=['GET', 'POST'])
@role_required(['HR Supervisor', 'HR Officer', 'Admin'])
def add_employee():
    if request.method == 'POST':
        df = read_employees()
        new_data = {
            "Employee ID": request.form['employee_id'],
            "Full Name": request.form['full_name'],
            "Position": request.form['position'],
            "Department": request.form['department'],
            "Date Hired": request.form['date_hired'],
            "Contact": request.form['contact'],
            "Status": request.form['status']
        }
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        save_employees(df)
        return redirect(url_for('hr.list_employees'))
    return render_template('hr/employee_form.html', action='Add', employee={})

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


import os
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename



DATA_FOLDER = 'data'
EMPLOYEE_FILE = os.path.join(DATA_FOLDER, 'employees.xlsx')
ATTENDANCE_FILE = os.path.join(DATA_FOLDER, 'attendance.xlsx')


def load_employee_dict():
    if os.path.exists(EMPLOYEE_FILE):
        df = pd.read_excel(EMPLOYEE_FILE)
        df_active = df[df['Status'].str.strip().str.lower() == 'active']
        return dict(zip(df_active['Employee ID'].astype(str), df_active['Full Name']))
    return {}


@hr_bp.route('/attendance', methods=['GET', 'POST'])
def attendance_tracking():
    emp_dict = load_employee_dict()

    if request.method == 'POST':
        form_data = request.form.to_dict()
        records = []

        i = 1
        while f'emp_number_{i}' in form_data:
            emp_number = form_data.get(f'emp_number_{i}', '').strip()
            if not emp_number:
                i += 1
                continue

            row = {
                'Date': form_data.get(f'date_{i}', ''),
                'Employee Number': emp_number,
                'Employee Name': emp_dict.get(emp_number, ''),
                'Basic Earnings': form_data.get(f'basic_{i}', 0),
                'Overtime': form_data.get(f'overtime_{i}', 0),
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
    emp_dict = load_employee_dict()
    name = emp_dict.get(emp_id.strip(), '')
    return jsonify({'name': name})


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

    if request.method == 'POST':
        emp_id = request.form.get('emp_id')
        start = request.form.get('start_date')
        end = request.form.get('end_date')
        filters.update({'emp_id': emp_id, 'start_date': start, 'end_date': end})

        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

            if emp_id:
                df = df[df['Employee Number'] == emp_id]
                df.columns = df.columns.str.strip()  # Strip any leading/trailing whitespace
            if start:
                df = df[df['Date'] >= pd.to_datetime(start)]
            if end:
                df = df[df['Date'] <= pd.to_datetime(end)]

            results = df.to_dict('records')

    # Employee dropdown list
    emp_df = pd.read_excel(EMPLOYEE_FILE) if os.path.exists(EMPLOYEE_FILE) else pd.DataFrame()
    emp_df = emp_df.dropna(subset=['Employee ID', 'Full Name'])
    emp_options = sorted(emp_df[['Employee ID', 'Full Name']].values.tolist(), key=lambda x: (x[1], x[0]))

    return render_template('hr/attendance_report.html', records=results, emp_options=emp_options, filters=filters)

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
@role_required(['Agriculture Manager', 'Manager', 'HR Officer', 'Admin'])
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
@role_required(['Agriculture Manager', 'Manager', 'HR Officer' , 'Admin'])
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


# Route: modules/hr.py (or relevant HR Blueprint file)
from flask import Blueprint, render_template
import pandas as pd
import os



DATA_DIR = 'data'  # Ensure this is the same directory used for storing Excel files

@hr_bp.route('/hr/reports')
def hr_reports():
    tables = {
        "employee_summary": "",
        "attendance_summary": "",
        "payroll_summary": "",
        "leave_summary": "",
        "task_summary": ""
    }

    try:
        # Load and convert Employee Summary
        employee_df = pd.read_excel(os.path.join(DATA_DIR, 'employees.xlsx'))
        tables['employee_summary'] = employee_df.to_html(classes='table table-bordered', index=False)

        # Attendance Summary
        attendance_df = pd.read_excel(os.path.join(DATA_DIR, 'attendance.xlsx'))
        tables['attendance_summary'] = attendance_df.to_html(classes='table table-striped', index=False)

        # Payroll Summary
        payroll_df = pd.read_excel(os.path.join(DATA_DIR, 'payroll.xlsx'))
        tables['payroll_summary'] = payroll_df.to_html(classes='table table-hover', index=False)

        # Leave Summary
        leave_df = pd.read_excel(os.path.join(DATA_DIR, 'leave_records.xlsx'))
        tables['leave_summary'] = leave_df.to_html(classes='table table-sm', index=False)

        # Task Summary
        tasks_df = pd.read_excel(os.path.join(DATA_DIR, 'task_assignments.xlsx'))
        tables['task_summary'] = tasks_df.to_html(classes='table table-bordered', index=False)

    except Exception as e:
        print(f"Error loading HR report data: {e}")

    return render_template('hr/hr_reports.html', tables=tables)


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
    if not os.path.exists(EMPLOYEE_FILE):
        flash("Employee data file not found!", "danger")
        return render_template('hr/employee_profile.html', employees=[], selected_employee=None)

    df = pd.read_excel(EMPLOYEE_FILE)
    df.columns = df.columns.str.strip()
    employees = df["Full Name"].dropna().tolist()

    name = request.args.get("name")
    selected_employee = df[df["Full Name"] == name].iloc[0] if name in df["Full Name"].values else None

    retirement_info = ""
    near_retirement = False
    photo = None

    # Default empty DataFrames
    promotions = pd.DataFrame()
    discipline = pd.DataFrame()
    training = pd.DataFrame()
    appraisals = pd.DataFrame()
    leaves = pd.DataFrame()

    if selected_employee is not None:
        dob = selected_employee.get("Date of Birth")
        try:
            dob = pd.to_datetime(dob)
            retirement_date = dob.replace(year=dob.year + 60)
            years_left = (retirement_date - pd.Timestamp.now()).days // 365
            retirement_info = f"{years_left} years left ({retirement_date.date()})"
            near_retirement = years_left <= 2
        except:
            retirement_info = "Unknown"

        emp_num = str(selected_employee.get("Employee ID"))
        photo = f"{emp_num}.jpg" if os.path.exists(os.path.join(PHOTO_FOLDER, f"{emp_num}.jpg")) else None

        # Load other HR records
        try:
            promotions_df = pd.read_excel("promotions.xlsx")
            promotions = promotions_df[promotions_df["Name"] == name]
        except: pass

        try:
            discipline_df = pd.read_excel("discipline.xlsx")
            discipline = discipline_df[discipline_df["Name"] == name]
        except: pass

        try:
            training_df = pd.read_excel("training.xlsx")
            training = training_df[training_df["Name"] == name]
        except: pass

        try:
            appraisals_df = pd.read_excel("appraisals.xlsx")
            appraisals = appraisals_df[appraisals_df["Name"] == name]
        except: pass

        try:
            leaves_df = pd.read_excel("leave_records.xlsx")
            leaves = leaves_df[leaves_df["Name"] == name]
        except: pass

    return render_template('hr/employee_profile.html',
                           employees=employees,
                           selected_employee=selected_employee,
                           retirement_info=retirement_info,
                           near_retirement=near_retirement,
                           photo=photo,
                           promotions=promotions,
                           discipline=discipline,
                           training=training,
                           appraisals=appraisals,
                           leaves=leaves)
