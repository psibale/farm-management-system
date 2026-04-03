# ==============================
# REPLANT PLANNING MODULE (FULL UPGRADE 🔥)
# ==============================

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
import pandas as pd
import os
from datetime import datetime
from modules.season import get_active_season

replant_bp = Blueprint('replant', __name__, url_prefix='/replant')

# File paths
YIELD_FILE = 'data/yield_data.xlsx'
PLANTING_FILE = 'data/planting_records.xlsx'
STRESS_FILE = 'data/field_polygons.xlsx'
FIELDS_FILE = 'data/registered_fields.xlsx'
REPLANT_FILE = 'data/replant_plan.xlsx'


# ==============================
# HELPER: NEXT SEASON
# ==============================
def get_next_season(season):
    try:
        start, end = season.split('/')
        return f"{int(start)+1}/{int(end)+1}"
    except:
        return season


# ==============================
# INIT FILE
# ==============================
def init_replant_file():
    if not os.path.exists(REPLANT_FILE):
        df = pd.DataFrame(columns=[
            'Field', 'Analysis Season', 'Replant Season',
            'Priority', 'Reason', 'Recommended Action',
            'Planned Planting Date', 'Lock', 'Approved'
        ])
        df.to_excel(REPLANT_FILE, index=False)

# ==============================
# GROUP FUNCTION
# ==============================
def group_field(field):
    field = str(field).strip()
    if field.startswith('DG') and len(field) >= 7:
        return field[:-3] + '000'
    return field


# ==============================
# GENERATE PLAN
# ==============================
@replant_bp.route('/generate')
def generate_replant_plan():
    try:
        init_replant_file()

        # ==============================
        # ✅ GET SELECTED SEASON
        # ==============================
        selected_season = request.args.get('season') or get_active_season()
        selected_season = str(selected_season).strip()

        # 👉 Replant happens NEXT season
        replant_season = get_next_season(selected_season)

        # ==============================
        # LOAD DATA
        # ==============================
        yield_df = pd.read_excel(YIELD_FILE)
        planting_df = pd.read_excel(PLANTING_FILE)
        stress_df = pd.read_excel(STRESS_FILE)
        fields_df = pd.read_excel(FIELDS_FILE)
        existing_df = pd.read_excel(REPLANT_FILE)

        # Clean column names
        for df_ in [yield_df, planting_df, stress_df, fields_df, existing_df]:
            df_.columns = df_.columns.str.strip()

        # ==============================
        # ✅ ENSURE REQUIRED COLUMNS EXIST
        # ==============================
        required_cols = [
            'Field', 'Season', 'Priority', 'Reason',
            'Recommended Action', 'Planned Planting Date',
            'Lock', 'Approved'
        ]

        for col in required_cols:
            if col not in existing_df.columns:
                existing_df[col] = ''

        # Clean season column
        existing_df['Season'] = existing_df['Season'].astype(str).str.strip()

        # ==============================
        # ✅ FILTER BY SELECTED SEASON
        # ==============================
        if 'Season' in yield_df.columns:
            yield_df['Season'] = yield_df['Season'].astype(str).str.strip()
            yield_df = yield_df[yield_df['Season'] == selected_season].copy()

        if 'Season' in fields_df.columns:
            fields_df['Season'] = fields_df['Season'].astype(str).str.strip()
            fields_df = fields_df[fields_df['Season'] == selected_season].copy()

        # ==============================
        # ✅ SAFE NUMERIC CONVERSION
        # ==============================
        yield_df['Yield (Tons)'] = pd.to_numeric(
            yield_df.get('Yield (Tons)', 0), errors='coerce'
        ).fillna(0)

        fields_df['Hectares'] = pd.to_numeric(
            fields_df.get('Hectares', 0), errors='coerce'
        ).fillna(0)

        fields_df['Crop Age'] = pd.to_numeric(
            fields_df.get('Crop Age', 0), errors='coerce'
        ).fillna(0)

        # ==============================
        # GROUP FIELDS
        # ==============================
        all_fields = set(yield_df['Field']).union(set(fields_df['Field']))
        grouped_data = {}

        for f in all_fields:
            grp = group_field(f)
            grouped_data.setdefault(grp, []).append(f)

        results = []

        # ==============================
        # PROCESS EACH FIELD GROUP
        # ==============================
        for grp, sub_fields in grouped_data.items():

            # 🔍 Check existing record (same FIELD + SAME REPLANT SEASON)
            match = existing_df[
                (existing_df['Field'] == grp) &
                (existing_df['Season'] == replant_season)
            ]

            existing_row = match.iloc[0] if not match.empty else None

            # 🔒 LOCK CHECK
            if existing_row is not None and str(existing_row.get('Lock', '')).lower() == 'yes':
                results.append(existing_row.to_dict())
                continue

            # ==============================
            # CALCULATIONS
            # ==============================
            y = yield_df[yield_df['Field'].isin(sub_fields)]['Yield (Tons)'].sum()
            a = fields_df[fields_df['Field'].isin(sub_fields)]['Hectares'].sum()

            tch = y / a if a > 0 else 0

            age = fields_df[fields_df['Field'].isin(sub_fields)]['Crop Age'].max()
            if pd.isna(age):
                age = 0

            # Stress
            if 'Stress Level' in stress_df.columns:
                s_rows = stress_df[
                    stress_df['Field'].isin(sub_fields)
                ]['Stress Level'].astype(str).str.lower()

                stress = (
                    'High' if 'high' in s_rows.values else
                    'Medium' if 'medium' in s_rows.values else
                    'Low'
                )
            else:
                stress = 'Low'

            threshold = 80 if grp.startswith('DG') else 40

            priority = 'Low'
            reason = []

            if tch < threshold:
                priority = 'High'
                reason.append(f'Low yield ({tch:.1f})')

            if stress == 'High':
                priority = 'High'
                reason.append('High stress')

            if age >= 9 and tch < threshold:
                priority = 'High'
                reason.append('Old ratoon')

            if priority != 'High':
                if (tch < threshold + 10) or stress == 'Medium' or age >= 9:
                    priority = 'Medium'

            # ==============================
            # SAVE RESULT
            # ==============================
            if priority != 'Low':

                planned = ''
                lock_val = ''
                approved_val = ''

                if existing_row is not None:
                    planned = existing_row.get('Planned Planting Date', '')
                    lock_val = existing_row.get('Lock', '')
                    approved_val = existing_row.get('Approved', '')

                results.append({
                    'Field': grp,
                    'Season': replant_season,   # ✅ unified column
                    'Priority': priority,
                    'Reason': ', '.join(reason),
                    'Recommended Action': 'Replant' if priority == 'High' else 'Monitor',
                    'Planned Planting Date': planned,
                    'Lock': lock_val,
                    'Approved': approved_val
                })

        # ==============================
        # ✅ SAFE CONCAT (REPLACE SAME SEASON)
        # ==============================
        old = existing_df[existing_df['Season'] != replant_season].copy()

        new_df = pd.DataFrame(results)

        df = pd.concat([old, new_df], ignore_index=True)

        # ==============================
        # SORT
        # ==============================
        order = {'High': 1, 'Medium': 2, 'Low': 3}
        df['Rank'] = df['Priority'].map(order)

        df = df.sort_values(by=['Season', 'Rank']).drop(columns=['Rank'])

        # ==============================
        # SAVE
        # ==============================
        df.to_excel(REPLANT_FILE, index=False)

        flash(f'✅ Replant plan generated for {replant_season}', 'success')

    except Exception as e:
        print("GENERATE ERROR:", str(e))
        flash(str(e), 'danger')

    return redirect(url_for('replant.view_replant_plan', season=replant_season))

# ==============================
# VIEW PLAN (WITH FILTER)
# ==============================
@replant_bp.route('/')
def view_replant_plan():
    try:
        init_replant_file()

        df = pd.read_excel(REPLANT_FILE)
        df.columns = df.columns.str.strip()

        # ==============================
        # ✅ GET SELECTED SEASON
        # ==============================
        selected_season = request.args.get('season') or get_active_season()
        selected_season = str(selected_season).strip()

        # ==============================
        # ✅ ENSURE SEASON COLUMN EXISTS
        # ==============================
        if 'Season' in df.columns:

            # Clean season values
            df['Season'] = df['Season'].astype(str).str.strip()

            # Get all available seasons
            seasons = sorted(df['Season'].dropna().unique())

            # Filter by selected season
            df = df.loc[df['Season'] == selected_season].copy()

        else:
            seasons = []
            selected_season = None

        # ==============================
        # ✅ OUTPUT
        # ==============================
        records = df.to_dict(orient='records')

        return render_template(
            'replant_plan.html',
            records=records,
            seasons=seasons,
            selected_season=selected_season
        )

    except Exception as e:
        flash(str(e), 'danger')
        print("VIEW REPLANT ERROR:", str(e))
        return redirect(url_for('agriculture.dashboard'))

# ==============================
# UPDATE DATE
# ==============================
@replant_bp.route('/update_date', methods=['POST'])
def update_date():
    field = request.form['field']
    date = request.form['date']

    df = pd.read_excel(REPLANT_FILE)
    df.loc[df['Field'] == field, 'Planned Planting Date'] = date
    df.to_excel(REPLANT_FILE, index=False)

    flash('Updated!', 'success')
    return redirect(url_for('replant.view_replant_plan'))


# ==============================
# TOGGLE LOCK (FIXED 🔥)
# ==============================
@replant_bp.route('/toggle_lock', methods=['POST'])
def toggle_lock():
    field = request.form['field']

    df = pd.read_excel(REPLANT_FILE)

    if 'Lock' not in df.columns:
        df['Lock'] = ''

    current = df.loc[df['Field'] == field, 'Lock'].values[0]
    df.loc[df['Field'] == field, 'Lock'] = 'No' if str(current).lower() == 'yes' else 'Yes'

    df.to_excel(REPLANT_FILE, index=False)

    flash(f"{field} lock updated", 'success')
    return redirect(url_for('replant.view_replant_plan'))


# ==============================
# SUMMARY
# ==============================
@replant_bp.route('/summary')
def replant_summary():
    df = pd.read_excel(REPLANT_FILE)
    summary = df.groupby('Priority').agg(Total_Fields=('Field', 'count')).reset_index()
    return render_template('replant_summary.html', summary=summary)


# ==============================
# DG DETAILS
# ==============================
@replant_bp.route('/dg_details')
def dg_details():
    df = pd.read_excel(REPLANT_FILE)
    dg = df[df['Field'].str.startswith('DG')]
    return render_template('replant_dg_details.html', records=dg.to_dict(orient='records'))


# ==============================
# PROGRESS DASHBOARD
# ==============================
@replant_bp.route('/progress_dashboard')
def progress_dashboard():
    try:
        active_season = get_active_season()

        # ✅ Get selected season from URL
        selected_season = request.args.get('season') or active_season

        # ==============================
        # LOAD DATA
        # ==============================
        tractor = pd.read_excel('data/tractor_operations.xlsx')
        planting = pd.read_excel(PLANTING_FILE)
        fields = pd.read_excel(FIELDS_FILE)
        replant = pd.read_excel(REPLANT_FILE)

        # Clean column names
        for df in [tractor, planting, fields, replant]:
            df.columns = df.columns.str.strip()

        # ==============================
        # FORCE NUMERIC (🔥 FIX ERROR)
        # ==============================
        numeric_cols = [
            'Area (ha)', 'Hour Meter Open', 'Hour Meter Closed',
            'Planted Area (ha)', 'Hectares'
        ]

        for col in numeric_cols:
            if col in tractor.columns:
                tractor[col] = pd.to_numeric(tractor[col], errors='coerce')
            if col in planting.columns:
                planting[col] = pd.to_numeric(planting[col], errors='coerce')
            if col in fields.columns:
                fields[col] = pd.to_numeric(fields[col], errors='coerce')

        # Fill NaN with 0
        tractor.fillna(0, inplace=True)
        planting.fillna(0, inplace=True)
        fields.fillna(0, inplace=True)

        # ==============================
        # GET AVAILABLE SEASONS
        # ==============================
        seasons = sorted(
            set(tractor.get('Season', []))
            | set(planting.get('Season', []))
            | set(fields.get('Season', []))
        )

        # ==============================
        # FILTER BY SELECTED SEASON
        # ==============================
        tractor = tractor[tractor['Season'] == selected_season].copy()
        planting = planting[planting['Season'] == selected_season].copy()
        fields = fields[fields['Season'] == selected_season].copy()

        if 'Season' in replant.columns:
            replant = replant[replant['Season'] == selected_season].copy()

        # ==============================
        # TRACTOR SUMMARY
        # ==============================
        tractor['Activity'] = tractor['Activity'].astype(str).str.lower()

        ripping = tractor[tractor['Activity'].str.contains('rip', na=False)]['Area (ha)'].sum()
        harrowing = tractor[tractor['Activity'].str.contains('harrow', na=False)]['Area (ha)'].sum()
        ridging = tractor[tractor['Activity'].str.contains('ridge', na=False)]['Area (ha)'].sum()

        tractor['Hours'] = tractor['Hour Meter Closed'] - tractor['Hour Meter Open']
        total_hours = tractor['Hours'].sum()

        efficiency = (ripping + harrowing + ridging) / total_hours if total_hours > 0 else 0

        # ==============================
        # PLANTING SUMMARY
        # ==============================
        planted_area = planting['Planted Area (ha)'].sum()

        labour_cols = ['Capitao','Planters','Choppers','Gleaners','Water Drawers','Tools Keeper','Transporters']
        for col in labour_cols:
            if col not in planting.columns:
                planting[col] = 0

        planting[labour_cols] = planting[labour_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
        planting['Total Labour'] = planting[labour_cols].sum(axis=1)
        total_labour = planting['Total Labour'].sum()

        planted_area = round(planted_area, 3)
        ripping = round(ripping, 2)
        harrowing = round(harrowing, 2)
        ridging = round(ridging, 2)
        efficiency = round(efficiency, 2)
        total_hours = round(total_hours, 2)

        # ==============================
        # DAILY RATE
        # ==============================
        if not planting.empty:
            planting['Date'] = pd.to_datetime(planting['Date'], errors='coerce')
            days_worked = planting['Date'].nunique()
            total_planted = planting['Planted Area (ha)'].sum()
            daily_rate = total_planted / days_worked if days_worked > 0 else 0
        else:
            daily_rate = 0

        # ==============================
        # GROUP FIELDS (DG logic)
        # ==============================
        def group_field(field):
            field = str(field).strip()
            if field.startswith('DG') and len(field) >= 7:
                return field[:-3] + '000'
            return field

        fields['Group'] = fields['Field'].apply(group_field)
        planting['Group'] = planting['Field'].apply(group_field)
        replant['Group'] = replant['Field'].apply(group_field)

        # ==============================
        # ONLY APPROVED FIELDS
        # ==============================
        if 'Approved' in replant.columns:
            approved_replant = replant[replant['Approved'].astype(str).str.upper() == 'YES']
        else:
            approved_replant = pd.DataFrame()

        target_fields = approved_replant['Group'].unique()

        # ==============================
        # PROGRESS PER FIELD
        # ==============================
        records = []

        for field in target_fields:
            planned = fields[fields['Group'] == field]['Hectares'].sum()
            actual = planting[planting['Group'] == field]['Planted Area (ha)'].sum()

            percent = (actual / planned * 100) if planned > 0 else 0

            # Status
            if percent < 30:
                status = 'Behind'
            elif percent < 80:
                status = 'In Progress'
            else:
                status = 'On Track'

            # Forecast
            remaining = planned - actual
            days_to_finish = remaining / daily_rate if daily_rate > 0 else 0

            records.append({
                'Field': field,
                'Planned Area': round(planned, 2),
                'Actual Planted': round(actual, 2),
                '% Complete': round(percent, 1),
                'Status': status,
                'Forecast Days': round(days_to_finish, 1) if days_to_finish > 0 else 0
            })

        # ==============================
        # SMART ALERTS
        # ==============================
        alerts = []

        land_prep_total = ripping + harrowing + ridging
        if planted_area < land_prep_total * 0.5:
            alerts.append("⚠️ Planting is lagging behind land preparation")

        behind_count = sum(1 for r in records if r['Status'] == 'Behind')
        if len(records) > 0 and behind_count > len(records) * 0.3:
            alerts.append("🚨 Many fields are behind schedule")

        if efficiency < 0.5:
            alerts.append("⚠️ Low tractor efficiency detected")

        # ==============================
        # RENDER
        # ==============================
        return render_template(
            'replant_master_dashboard.html',
            ripping=ripping,
            harrowing=harrowing,
            ridging=ridging,
            planted_area=planted_area,
            total_labour=total_labour,
            total_hours=total_hours,
            efficiency=round(efficiency, 2),
            records=records,
            alerts=alerts,
            seasons=seasons,
            selected_season=selected_season
        )

    except Exception as e:
        flash(str(e), 'danger')
        print("PROGRESS DASHBOARD ERROR:", str(e))
        return redirect(url_for('replant.view_replant_plan'))

# ==============================
# ADD MANUAL FIELD (RESTORED 🔥)
# ==============================

@replant_bp.route('/add_manual', methods=['POST'])
def add_manual():
    try:
        field = request.form['field'].strip()
        priority = request.form['priority']
        reason = request.form['reason'].strip()
        date = request.form['date']
        lock = request.form.get('lock', '')

        # ✅ Selected season = replant season now
        selected_season = request.args.get('season') or get_next_season(get_active_season())

        df = pd.read_excel(REPLANT_FILE)
        df.columns = df.columns.str.strip()

        # ✅ Ensure required columns exist
        required_cols = [
            'Field', 'Season', 'Priority', 'Reason',
            'Recommended Action', 'Planned Planting Date',
            'Lock', 'Approved'
        ]

        for col in required_cols:
            if col not in df.columns:
                df[col] = ''

        # ==============================
        # CHECK DUPLICATE
        # ==============================
        exists = df[
            (df['Field'] == field) &
            (df['Season'] == selected_season)
        ]

        if not exists.empty:
            flash(f"{field} already exists for {selected_season}.", 'warning')

        else:
            # ==============================
            # CREATE NEW ROW
            # ==============================
            new_row = {
                'Field': field,
                'Season': selected_season,   # ✅ KEY FIX
                'Priority': priority,
                'Reason': reason,
                'Recommended Action': 'Replant',
                'Planned Planting Date': date,
                'Lock': lock,
                'Approved': ''
            }

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

            df.to_excel(REPLANT_FILE, index=False)

            flash(f"{field} added for {selected_season} ✅", 'success')

    except Exception as e:
        flash(f"Error adding manual field: {str(e)}", 'danger')
        print("MANUAL REPLANT ERROR:", str(e))

    return redirect(url_for('replant.view_replant_plan', season=selected_season))

# ==============================
# REPLANT COMPARISON
# ==============================
@replant_bp.route('/comparison')
def replant_comparison():
    try:
        df = pd.read_excel(REPLANT_FILE)
        yield_df = pd.read_excel(YIELD_FILE)

        # Clean columns
        df.columns = df.columns.str.strip()
        yield_df.columns = yield_df.columns.str.strip()

        # ==============================
        # ✅ GET SELECTED SEASON
        # ==============================
        selected_season = request.args.get('season') or get_active_season()
        selected_season = str(selected_season).strip()

        # ==============================
        # ✅ PREPARE DATA (SAFE TYPES)
        # ==============================
        df['Season'] = df['Season'].astype(str).str.strip()
        yield_df['Season'] = yield_df['Season'].astype(str).str.strip()
        yield_df['Field'] = yield_df['Field'].astype(str).str.strip()

        # ✅ Convert yield once (NOT inside loop)
        yield_df['Yield (Tons)'] = pd.to_numeric(
            yield_df['Yield (Tons)'], errors='coerce'
        ).fillna(0)

        # ==============================
        # ✅ GET ALL SEASONS (for dropdown)
        # ==============================
        seasons = sorted(df['Season'].dropna().unique())

        # ==============================
        # ✅ FILTER REPLANT DATA
        # ==============================
        df = df[df['Season'] == selected_season]

        # ✅ Only APPROVED fields
        if 'Approved' in df.columns:
            df = df[df['Approved'] == 'Yes']

        results = []

        for _, row in df.iterrows():

            field = str(row['Field']).strip()
            replant_season = row['Season']

            # ==============================
            # BEFORE = SAME SEASON
            # ==============================
            before_season = replant_season

            # ==============================
            # AFTER = NEXT SEASON
            # ==============================
            after_season = get_next_season(replant_season)

            # ==============================
            # YIELD CALCULATIONS
            # ==============================
            before_yield = yield_df[
                (yield_df['Field'] == field) &
                (yield_df['Season'] == before_season)
            ]['Yield (Tons)'].sum()

            after_yield = yield_df[
                (yield_df['Field'] == field) &
                (yield_df['Season'] == after_season)
            ]['Yield (Tons)'].sum()

            improvement = after_yield - before_yield

            results.append({
                'Field': field,
                'Before Season': before_season,
                'After Season': after_season,
                'Priority': row.get('Priority', ''),
                'Before Yield': round(before_yield, 1),
                'After Yield': round(after_yield, 1),
                'Improvement': round(improvement, 1)
            })

        return render_template(
            'replant_comparison.html',
            records=results,
            seasons=seasons,
            selected_season=selected_season
        )

    except Exception as e:
        flash(str(e), 'danger')
        print("COMPARISON ERROR:", str(e))
        return redirect(url_for('replant.view_replant_plan'))
    
# ==============================
# TOGGLE APPROVAL
# ==============================
@replant_bp.route('/toggle_approval', methods=['POST'])
def toggle_approval():
    field = request.form['field']

    df = pd.read_excel(REPLANT_FILE)

    if 'Approved' not in df.columns:
        df['Approved'] = ''

    current = df.loc[df['Field'] == field, 'Approved'].values[0]

    new_status = 'Yes' if str(current).lower() != 'yes' else 'No'

    df.loc[df['Field'] == field, 'Approved'] = new_status

    df.to_excel(REPLANT_FILE, index=False)

    flash(f"{field} approval set to {new_status}", 'success')

    return redirect(url_for('replant.view_replant_plan'))

@replant_bp.route('/bulk_approve', methods=['POST'])
def bulk_approve():
    selected = request.form.getlist('selected_fields')
    if not selected:
        flash("No fields selected for approval.", "warning")
        return redirect(url_for('replant.progress_dashboard'))

    replant = pd.read_excel(REPLANT_FILE)
    replant['Approved'] = replant.apply(lambda row: 'Yes' if row['Field'] in selected else row.get('Approved', ''), axis=1)
    replant.to_excel(REPLANT_FILE, index=False)
    flash(f"{len(selected)} field(s) approved successfully!", "success")
    return redirect(url_for('replant.progress_dashboard'))