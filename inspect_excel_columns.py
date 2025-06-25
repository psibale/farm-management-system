import pandas as pd
import os

# File paths (adjust as needed)
EMPLOYEE_FILE = 'employee_data.xlsx'
GRADE_RULES_FILE = 'grade_rules.xlsx'
LEAVE_FILE = 'data/leave_records.xlsx'


def inspect_file(filepath, name):
    print(f"\n🔍 Inspecting: {name} ({filepath})")

    if not os.path.exists(filepath):
        print("❌ File does not exist.")
        return

    try:
        df = pd.read_excel(filepath, header=0)
        cleaned_columns = [str(col).strip() for col in df.columns]
        print("✅ Found columns:")
        for col in cleaned_columns:
            print(f"  - '{col}'")
    except Exception as e:
        print("❌ Error reading file:", e)


def main():
    inspect_file(EMPLOYEE_FILE, 'EMPLOYEE_FILE')
    inspect_file(GRADE_RULES_FILE, 'GRADE_RULES_FILE')
    inspect_file(LEAVE_FILE, 'LEAVE_FILE')


if __name__ == '__main__':
    main()
