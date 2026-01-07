import pandas as pd
import os
import sys

# Try importing xlrd, if implies dependency issue, we might need to install it
try:
    import xlrd
except ImportError:
    print("xlrd not found. Please install it.")
    # In this environment I cannot install easily? 
    # I will rely on run_command to output error and then I might suggest user to install or I try pip install
    pass

file_path = '/Users/remzi/Desktop/BekoSIRS/BekoSIRS_api/bekoproducts.xls'

try:
    if not os.path.exists(file_path):
        print(f"File NOT found at {file_path}")
        sys.exit(1)
        
    print(f"Reading {file_path}...")
    xls = pd.ExcelFile(file_path)
    sheet_names = xls.sheet_names
    print(f"Sheets found: {sheet_names}")

    with open('excel_analysis_output.txt', 'w') as f:
        f.write(f"File: {file_path}\n")
        f.write(f"Sheets: {sheet_names}\n")
        
        for sheet in sheet_names:
            f.write(f"\n{'='*50}\nSHEET: {sheet}\n{'='*50}\n")
            df = pd.read_excel(xls, sheet_name=sheet)
            
            f.write(f"Shape: {df.shape} (Rows, Columns)\n")
            f.write(f"Columns: {list(df.columns)}\n\n")
            
            f.write("--- Data Types ---\n")
            f.write(df.dtypes.to_string())
            f.write("\n\n")
            
            f.write("--- Missing Values ---\n")
            f.write(df.isnull().sum().to_string())
            f.write("\n\n")
            
            f.write("--- Sample Data (First 5) ---\n")
            f.write(df.head().to_string())
            f.write("\n\n")
            
            # Basic profiling
            f.write("--- Column Profiling ---\n")
            for col in df.columns:
                unique_count = df[col].nunique()
                f.write(f"{col}: {unique_count} unique values\n")
                if unique_count < 10:
                    f.write(f"   Values: {list(df[col].unique())}\n")
            f.write("\n")

    print("Analysis complete. Check excel_analysis_output.txt")
    print(open('excel_analysis_output.txt').read())

except Exception as e:
    print(f"Error: {e}")
