import pandas as pd
import json
import os
import re

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE_DIR)

SOURCE_EXCEL = os.path.join(
    REPO_ROOT, 
    "engineering_tools/mech_core/standards/data/aisc-shapes-database-v16.0.xlsx"
)
OUTPUT_JSON = os.path.join(
    REPO_ROOT, 
    "engineering_tools/mech_core/standards/data/aisc_shapes.json"
)

def clean_value(val):
    """
    Robust value cleaner.
    """
    if pd.isna(val): return None
    val_str = str(val).strip()
    if val_str in ['–', '-', 'N/A', '', 'None']:
        return None
    try:
        f_val = float(val)
        if f_val.is_integer():
            return int(f_val)
        return f_val
    except ValueError:
        return val_str

def convert_aisc_to_json():
    print(f"--- AISC Database Ingestion (Vacuum Mode) ---")
    
    if not os.path.exists(SOURCE_EXCEL):
        print(f"[ERROR] File not found: {SOURCE_EXCEL}")
        return

    print("Reading Excel...")
    df = pd.read_excel(SOURCE_EXCEL, sheet_name=1, header=0)
    
    # 1. Clean Headers
    # Replace spaces, slashes, and parentheses to make valid JSON keys
    # e.g. "tan(α)" -> "tan_alpha", "twdet/2" -> "twdet_2"
    df.columns = (df.columns.str.strip()
                  .str.replace(' ', '_')
                  .str.replace('/', '_')
                  .str.replace('(', '')
                  .str.replace(')', '')
                  .str.replace('α', 'alpha'))
    
    relevant_types = ["W", "M", "S", "HP", "C", "MC", "L", "WT", "MT", "ST", "2L", "HSS", "PIPE"]
    df = df[df["Type"].isin(relevant_types)]
    
    print(f"Found {len(df)} shapes. Mapping columns...")

    # 2. Identify Property Pairs
    # Pandas names the second occurrence "Name.1". This is our Metric column.
    all_cols = list(df.columns)
    base_props = []
    
    for col in all_cols:
        if col.endswith('.1'):
            base = col[:-2] 
            if base not in base_props:
                base_props.append(base)
        else:
            # If it's not a duplicate, and not a known metadata column, add it?
            # Actually, to handle the 'Unpaired' columns (like T_F), we just check existence later.
            if col not in base_props:
                base_props.append(col)

    database = {}
    count = 0

    for idx, row in df.iterrows():
        try:
            # --- NAME HANDLING ---
            # Imperial Name (Primary Key)
            if "AISC_Manual_Label" in row:
                name_imp = str(row["AISC_Manual_Label"]).strip().upper()
            else:
                continue

            # Metric Name (From the duplicate column)
            # We look for "EDI_Std_Nomenclature.1" (or whatever case it parsed as)
            name_met = ""
            
            # Check for the duplicate column for Metric Name
            # The header cleaning might have changed "EDI_Std_ Nomenclature" to "EDI_Std_Nomenclature"
            if "EDI_Std_Nomenclature.1" in row:
                val = row["EDI_Std_Nomenclature.1"]
                if not pd.isna(val):
                    name_met = str(val).strip().upper()
            
            # Fallback: sometimes the duplicate might be named differently depending on exact header char
            if not name_met and "EDI_STD_Nomenclature.1" in row:
                 val = row["EDI_STD_Nomenclature.1"]
                 if not pd.isna(val):
                    name_met = str(val).strip().upper()

            # --- PROPERTY VACUUM ---
            shape_data = {
                "name_imperial": name_imp,
                "name_metric": name_met,
                "type": row["Type"]
            }

            for prop in base_props:
                # Skip metadata we already handled
                if prop in ["Type", "AISC_Manual_Label", "EDI_Std_Nomenclature", "EDI_STD_Nomenclature", "T_F"]:
                    continue

                col_imp = prop
                col_met = f"{prop}.1"
                
                # Check if this property has a Metric Pair
                if col_met in row:
                    val_m = clean_value(row[col_met])
                    val_i = clean_value(row[col_imp])
                    
                    # Store Metric as standard, Imperial with suffix
                    if val_m is not None:
                        shape_data[prop] = val_m
                    if val_i is not None:
                        shape_data[f"{prop}_imp"] = val_i
                
                # Check if it's a standalone column (only exists once)
                elif col_imp in row:
                    val = clean_value(row[col_imp])
                    if val is not None:
                        shape_data[prop] = val

            database[name_imp] = shape_data
            count += 1
            
        except Exception as e:
            # print(f"Skipping row {idx}: {e}")
            continue

    # Save
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(database, f, indent=0)

    print(f"Success! Processed {count} shapes.")
    
    # VERIFICATION
    test_key = "W44X408"
    if test_key in database:
        print(f"--- VERIFICATION FOR {test_key} ---")
        print(f"Metric Name: '{database[test_key].get('name_metric')}' (Expect W1100...)")
        print(f"Depth (d):    {database[test_key].get('d')} (Expect ~1140)")
        print(f"Shear Ctr (eo): {database[test_key].get('eo')} (Vacuum check)")

if __name__ == "__main__":
    convert_aisc_to_json()