from pathlib import Path
import pandas as pd

# ============================================================
# 1. PROJECT PATHS
# ============================================================

try: 
    ROOT_DIR = Path(__file__).resolve().parents[2]
except NameError:
    ROOT_DIR = Path.cwd().parent

RAW_DIR = ROOT_DIR / "data" / "raw"

REPORT_DIR = ROOT_DIR / "reports" / "data_profiling"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 2. DATE COLUMN DETECTION
# ============================================================

DATE_KEYWORDS = {
    "date",
    "datetime",
    "timestamp",
    "dispatch",
    "purchase",
    "termination",
    "delivery",
    "departure",
    "arrival",
    "service",
    "hire_date",
    "start_time",
    "end_time",
    "contract_start_date",
    "month",
    "purchase_date",
    "load_date",
    "incident_date",
    "dispatch_date",
    "termination_date",
    "date_of_birth",
    "maintenance_date",
    "acquisition_date",
}


def is_date_column(column_name):
    """Identify columns that are likely to contain dates"""

    name = column_name.lower()

    return any(
        keyword in name
        for keyword in DATE_KEYWORDS
    )


# ============================================================
# 3. FIND SOURCE FILES
# ============================================================

csv_files = sorted(RAW_DIR.glob("*.csv"))

if not csv_files:
    raise FileNotFoundError(
        f"No CSV files found in: {RAW_DIR}"
    )

print(f"Found {len(csv_files)} CSV files.\n")




# ============================================================
# 4. INITIALISE REPORT COLLECTIONS
# ============================================================

table_inventory = []
column_profile = []
date_coverage = []

# ============================================================
# 5. PROFILE EACH CSV
# ============================================================

for file_path in csv_files:

    table_name = file_path.stem

    print(f"Profiling: {file_path.name}")

    try: 
        df = pd.read_csv(
            file_path,
            low_memory=False
        )

        # ----------------------------------------------------
        # TABLE-LEVEL PROFILING
        # ----------------------------------------------------

        table_inventory.append({
            "table_name": table_name,
            "file_name": file_path.name,
            "file_size_mb": round(
                file_path.stat().st_size / (1024 ** 2),
                3
            ),

            "row_count": len(df),
            "column_count": len(df.columns),
            "duplicated_rows": int(
                df.duplicated().sum()
            ),
            "total_missing_percentage": round(
                df.isna().sum().sum()/ (df.shape[0] * df.shape[1]) * 100, 2
            ) if df.size else 0
            
        })

        # ----------------------------------------------------
            # COLUMN-LEVEL PROFILING
        # ----------------------------------------------------

        for column in df.columns:
            
            series = df[column]

            non_nulls_values = series.dropna()

            sample_values = (
                non_nulls_values.astype(str)
                .drop_duplicates()
                .head()
                .tolist()
            )

            column_profile.append({
                "table_name": table_name,
                'column_name': column,
                'inferred_data_type': str(
                    series.dtype
                ),

                'total_values': len(series),
                'missing_values': int(
                    series.isna().sum()
                ),
                "missing_percentage": round(
                    series.isna().mean() * 100,
                    2
                ),
                'unique_values': int(
                    series.nunique(dropna=True)
                ),
                "distinct_values_including_null": int(
                    series.nunique(dropna=False)
                ),
                "sample_values": " | ".join(sample_values)
            })
            
            # ------------------------------------------------
            # DATE-LEVEL PROFILING
            # ------------------------------------------------
            if is_date_column(column):

                parsed_date = pd.to_datetime(
                    series,
                    errors='coerce',
                    dayfirst=True,
                    format='mixed'
                )

                valid_dates = parsed_date.dropna()

                invalid_dates = int(
                    (series.notna() & parsed_date.isna()).sum()
                )

                date_coverage.append({
                    'table_name': table_name,

                    'column_name': column,

                    'valid_dates': len(valid_dates),

                    'missing_dates': int(
                        series.isna().sum()
                    ),

                    'invalid_dates': invalid_dates,

                    'minimum_date': (
                        valid_dates.min()
                        if not valid_dates.empty
                        else None
                    ),

                    'maximum_date': (
                        valid_dates.max()
                        if not valid_dates.empty
                        else None
                    )
                })
                
    except Exception as error:
        print(f"ERROR processing {file_path.name}: {error}")


# ============================================================
# 6. EXPORT REPORTS
# ============================================================

inventory_df = pd.DataFrame(table_inventory)

column_df = pd.DataFrame(column_profile)

date_df = pd.DataFrame(date_coverage)


inventory_df.to_csv(
    REPORT_DIR / "table_inventory.csv",
    index=False
)

column_df.to_csv(
    REPORT_DIR / "column_profile.csv",
    index=False
)

date_df.to_csv(
    REPORT_DIR / 'date_coverage.csv',
    index=False
)


# ============================================================
# 7. COMPLETION SUMMARY
# ============================================================

print("\n" + "=" * 50)

print("DATA PROFILING COMPLETED")

print("=" * 50)

print(f"Files processed: {len(table_inventory)}")

print(f"Tables profiled: {len(inventory_df)}")

print(f"Columns profiled: {len(column_df)}")

print(f"Date columns identified: {len(date_df)}")

print(f"\nReports saved to: {REPORT_DIR}")

# Generate a data dictionary template
dictionary_template = column_df.copy()

dictionary_template["business_description"] = ""
dictionary_template["key_type"] = ""
dictionary_template["nullable"] = ""
dictionary_template["business_rules"] = ""
dictionary_template["transformation_notes"] = ""

dictionary_template.to_csv(
    REPORT_DIR / "data_dictionary_template.csv",
    index=False
)