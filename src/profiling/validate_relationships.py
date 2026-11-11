from pathlib import Path
import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

try:
    ROOT_DIR = Path(__file__).resolve().parents[2]
except:
    ROOT_DIR = Path.cwd().parent

RAW_DIR = ROOT_DIR / "data" / "raw"
REPORT_DIR = ROOT_DIR / 'reports' / 'data_profiling'

REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. DOCUMENTED PRIMARY KEYS
# ============================================================


PRIMARY_KEYS = {

    "drivers": ["driver_id"],

    "trucks": ["truck_id"],

    "trailers": ["trailer_id"],

    "customers": ["customer_id"],

    "facilities": ["facility_id"],

    "routes": ["route_id"],

    "loads": ["load_id"],

    "trips": ["trip_id"],

    "fuel_purchases": ["fuel_purchase_id"],

    "maintenance_records": ["maintenance_id"],

    "delivery_events": ["event_id"],

    "safety_incidents": ["incident_id"],

    "driver_monthly_metrics": [
        "driver_id", "month"
    ],

    "truck_utilization_metrics": [
        "truck_id", "month"
    ]

}


# ============================================================
# 3. DOCUMENTED FOREIGN-KEY RELATIONSHIPS
#
# Format:
# child table, child column, parent table, parent column
# ============================================================

RELATIONSHIPS = [
    ('loads', 'customer_id', 'customers', 'customer_id'),
    
    ('loads', 'route_id', 'routes', 'route_id'),
    
    ('trips', 'load_id', 'loads', 'load_id'),

    ('trips', 'driver_id', 'drivers', 'driver_id'),

    ('trips', 'truck_id', 'trucks', 'truck_id'),

    ('trips', 'trailer_id', 'trailers', 'trailer_id'),

    ('fuel_purchases', 'trip_id', 'trips', 'trip_id'),
    
    ("fuel_purchases", "driver_id", "drivers", "driver_id"),
    
    ("fuel_purchases", "truck_id", "trucks", "truck_id"),

    ("maintenance_records", "truck_id", "trucks", "truck_id"),

    ("delivery_events", "load_id", "loads", "load_id"),

    ("delivery_events", "trip_id", "trips", "trip_id"),

    ("delivery_events", "facility_id", "facilities", "facility_id"),

    ("safety_incidents", "trip_id", "trips", "trip_id"),

    ("safety_incidents", "truck_id", "trucks", "truck_id"),

    ("safety_incidents", "driver_id", "drivers", "driver_id"),

    ("driver_monthly_metrics", "driver_id", "drivers", "driver_id"),

    ("truck_utilization_metrics", "truck_id", "trucks", "truck_id")

]


# ============================================================
# 4. LOAD TABLES
# ============================================================

tables = {}

for file_path in RAW_DIR.glob("*.csv"):

    table_name = file_path.stem

    tables[table_name] = pd.read_csv(
        file_path,
        dtype='string',
        keep_default_na=True
    )

print(f"Loaded {len(tables)} tables.")


# ============================================================
# 5. PRIMARY AND COMPOSITE KEY VALIDATION
# ============================================================

key_results = []

for table_name, key_columns in PRIMARY_KEYS.items():

    if table_name not in tables:

        key_results.append({
            'table_name': table_name,

            "key_columns": " + ".join(key_columns),

            'duplicate_rows': None,

            'null_key_rows': None,

            'status': 'TABLE NOT FOUND'
        })

        continue

    df = tables[table_name]

    missing_columns = [
        col for col in key_columns
        if col not in df.columns
    ]

    if missing_columns:

        key_results.append({
             "table_name": table_name,

            "key_columns": " + ".join(key_columns),

            "duplicate_rows": None,

            "null_key_rows": None,

            'status': (
                'COLUMN NOT FOUND: ' + ", ".join(missing_columns)
            )
        })

        continue

            # Count records with duplicate key combinations
    duplicate_rows = int(
        df.duplicated(
            subset=key_columns,
            keep=False
        ).sum()
    )

    # Count records with at least one null key component
    null_key_rows = int(
        df[key_columns].isna().any(axis=1).sum()
    )

    status = (
        'PASS'

        if duplicate_rows == 0
        and null_key_rows == 0

        else 'INVESTIGATE'
    )

    key_results.append({
        'table_name': table_name,

        'key_columns': ' + '.join(key_columns),

        'duplicate_rows': duplicate_rows,

        'null_key_rows': null_key_rows,

        'status': status
    })


# ============================================================
# 6. FOREIGN KEY AND CARDINALITY VALIDATION
# ============================================================

relationship_results = []

for child, child_col, parent, parent_col in RELATIONSHIPS:

    # Check that both tables exist
    if child not in tables or parent not in tables: 

        relationship_results.append({
            'child_table': child,

            'child_column': child_col,

            'parent_table': parent,

            'parent_column': parent_col,

            'missing_fk': None,

            'orphan_rows': None,

            'duplicate_parent_rows': None,

            'observed_cardinality': 'NOT AVAILABLE',

            'status': 'TABLE NOT FOUND'
        })

        continue

    child_df = tables[child]

    parent_df = tables[parent]

    # Check that the required columns exist 
    if(
        child_col not in child_df.columns
        or parent_col not in parent_df.columns
    ):

        relationship_results.append({

            "child_table": child,

            "child_column": child_col,

            "parent_table": parent,

            "parent_column": parent_col,

            "missing_fk": None,

            "orphan_rows": None,

            "duplicate_parent_rows": None,

            "observed_cardinality": "NOT AVAILABLE",

            "status": "COLUMN NOT FOUND"

            
        })
        continue

    child_values = child_df[child_col]

    parent_values = parent_df[parent_col]

    # Count missing foreign keys
    missing_fk = int(
        child_values.isna().sum()
    )

    # Count child records referencing non-existent parents
    valid_parent_values = set(
        parent_values.dropna()
    )

    orphan_mask = (
        child_values.notna()
        & ~child_values.isin(valid_parent_values)
    )

    orphan_rows = int(orphan_mask.sum())

    # Check parent key uniqueness
    duplicate_parent_rows = int(
        parent_values.duplicated(keep=False).sum()
    )

    child_unique = (
        child_values.dropna().is_unique
    )

    parent_unique = (
        parent_values.dropna().is_unique
    )

    # Determine observed cardinality
    if child_unique and parent_unique:

        cardinality = '1:1'

    elif child_unique:

        cardinality = '1:M'

    elif parent_unique:

        cardinality = 'M:1'

    else:

        cardinality = 'M:M'

    # Determine mechanical validation status
    if(
        missing_fk == 0
        and orphan_rows == 0
        and duplicate_parent_rows == 0
    ):
        status = 'PASS'

    else:
        status = 'INVESTIGATE'

    relationship_results.append({
        'child_table': child,

        'child_column': child_col,

        'parent_table': parent,

        'parent_col': parent_col,

        'missing_fk': missing_fk,

        'orphan_rows': orphan_rows,

        'duplicated_parent_rows': duplicate_parent_rows,

        'observed_cardinality': cardinality,

        'status': status
    })


    # ============================================================
# 7. EXPORT VALIDATION REPORTS
# ============================================================

key_df = pd.DataFrame(key_results)

relationship_df = pd.DataFrame(
    relationship_results
)

key_df.to_csv(
    REPORT_DIR / "key_validation.csv",
    index=False
)

relationship_df.to_csv(
    REPORT_DIR / "relationship_validation.csv",
    index=False
)


# ============================================================
# 8. COMPLETION SUMMARY
# ============================================================

print("\n" + "=" * 55)

print("KEY AND RELATIONSHIP VALIDATION COMPLETED")

print("=" * 55)

print('\nPrimary key checks:')

print(key_df['status'].value_counts(dropna=False))

print("\nRelationship checks:")

print(
    relationship_df['status'].value_counts(dropna=False)
)

print(f'\nReports saved to: {REPORT_DIR}')