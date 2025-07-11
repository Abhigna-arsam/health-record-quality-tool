# -*- coding: utf-8 -*-
"""ehr_data_quality_auditor.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Ps9d-2RRfEMTzlskgOmzd_XcxXZromTY
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest
import json

# ------------------ Module 1: Load Data ------------------
def load_data(file_path):
    try:
        df = pd.read_csv(file_path)
        print(f"Loaded {len(df)} records from {file_path}")
        return df
    except Exception as e:
        print(f"Failed to load data: {e}")
        return None

# ------------------ Module 2: Missing Values Detection ------------------
def missing_value_analysis(df, zero_as_missing_cols, additional_missing_values=None):
    if additional_missing_values is None:
        additional_missing_values = ['', 'N/A', 'Unknown']
    df.replace(additional_missing_values, np.nan, inplace=True)

    missing_summary = {}
    for col in df.columns:
        missing_summary[col] = df[col].isnull().sum()

    for col in zero_as_missing_cols:
        zero_count = (df[col] == 0).sum()
        missing_summary[col + "_Zeros_as_Missing"] = zero_count
        df[col + "_Missing"] = df[col] == 0

    data_cols_count = len(df.columns) - sum(col.endswith('_Missing') for col in df.columns)

    def completeness(row):
        missing = row.isnull().sum()
        zero_miss = sum([row.get(col + "_Missing", False) for col in zero_as_missing_cols])
        total_missing = missing + zero_miss
        return 100 * (1 - total_missing / data_cols_count)

    df['Completeness_Score (%)'] = df.apply(completeness, axis=1)

    missing_df = pd.DataFrame.from_dict(missing_summary, orient='index', columns=['Missing_Count'])
    missing_df['Missing_%'] = 100 * missing_df['Missing_Count'] / len(df)
    return df, missing_df

# ------------------ Module 3: Outlier Detection ------------------
def detect_outliers_iqr(series):
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    return ~series.between(lower, upper)

def outlier_detection(df, cols):
    for col in cols:
        df[col + "_Outlier"] = detect_outliers_iqr(df[col])
    return df

# ------------------ Module 3b: Isolation Forest ------------------
def anomaly_detection_isolation_forest(df, cols, contamination=0.05, random_state=42):
    iso = IsolationForest(contamination=contamination, random_state=random_state)
    X = df[cols].copy().fillna(df[cols].median())
    preds = iso.fit_predict(X)
    df['Row_AnomalyIF'] = preds == -1
    return df

# ------------------ Module 4: Clinical Range Check ------------------
def clinical_range_check(df, ranges):
    for col, (low, high) in ranges.items():
        if col in df.columns:
            df[col + "_RangeError"] = ~df[col].between(low, high)
    return df

# ------------------ Module 5: Pattern/Format Validation ------------------
def pattern_and_format_checks(df):
    df['Age_FormatError'] = ~df['Age'].apply(lambda x: isinstance(x, (int, float, np.integer)) and 0 <= x <= 120)
    return df

# ------------------ Module 6: Scoring ------------------
def classify_errors_and_score(df, error_weights=None):
    error_cols = [col for col in df.columns if col.endswith(('_Missing', '_Outlier', '_RangeError', '_FormatError', '_AnomalyIF'))]
    if error_weights is None:
        error_weights = {col: 1 for col in error_cols}
    else:
        for col in error_cols:
            error_weights.setdefault(col, 1)

    df['Weighted_Errors'] = sum(df[col].astype(int) * error_weights[col] for col in error_cols)
    df['Total_Errors'] = df[error_cols].sum(axis=1)
    total_weight = sum(error_weights.values())
    df['Quality_Score (%)'] = 100 - (df['Weighted_Errors'] / total_weight * 100)

    def error_log(row):
        errors = []
        for col in error_cols:
            if row[col]:
                base_col = col.split('_')[0]
                value = row.get(base_col, 'N/A')
                errors.append(f"{col} ({value})")
        return "; ".join(errors) if errors else "No Errors"

    df.reset_index(inplace=True)
    df.rename(columns={'index': 'Row_Index'}, inplace=True)
    df['Error_Log'] = df.apply(error_log, axis=1)

    return df, error_cols

# ------------------ Module 7: Statistics ------------------
def statistical_summary(df, numeric_cols):
    return df[numeric_cols].describe().T[['mean', '50%', 'min', 'max']].rename(columns={'50%': 'median'})

# ------------------ Module 8: Reports ------------------
def generate_reports(df, error_cols, missing_df, stats_df,
                     output_detail="EHR_Data_Quality_Detailed_Report.csv",
                     output_error_log="EHR_Data_Quality_Error_Log.csv",
                     output_summary="EHR_Data_Quality_Summary.csv"):

    core_cols = ['Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI', 'Age']
    final_cols = ['Row_Index'] + core_cols + error_cols + ['Total_Errors', 'Weighted_Errors',
                                                            'Quality_Score (%)', 'Completeness_Score (%)', 'Error_Log']

    df[final_cols].to_csv(output_detail, index=False)
    df[['Row_Index', 'Error_Log']].to_csv(output_error_log, index=False)

    overall = {
        'Total Records': len(df),
        'Average Quality Score (%)': round(df['Quality_Score (%)'].mean(), 2),
        'Records with 0 Errors': int((df['Total_Errors'] == 0).sum()),
        'Records with >50% Errors': int((df['Quality_Score (%)'] < 50).sum()),
        'Average Completeness Score (%)': round(df['Completeness_Score (%)'].mean(), 2)
    }

    with open(output_summary, 'w') as f:
        f.write("=== Missing Data Summary ===\n")
        missing_df.to_csv(f)
        f.write("\n=== Statistical Summary ===\n")
        stats_df.to_csv(f)
        f.write("\n=== Overall Quality Metrics ===\n")
        for k, v in overall.items():
            f.write(f"{k},{v}\n")

    return overall

# ------------------ Module 9: Visualization ------------------
def visualize_data_quality(df, missing_df, numeric_cols):
    plt.figure(figsize=(18, 5))

    plt.subplot(1, 3, 1)
    sns.barplot(x=missing_df.index, y='Missing_Count', data=missing_df, palette='viridis')
    plt.xticks(rotation=45)
    plt.title('Missing / Zero Values')

    plt.subplot(1, 3, 2)
    sns.histplot(df['Completeness_Score (%)'], kde=True, bins=20, color='teal')
    plt.title('Completeness Score Distribution')

    plt.subplot(1, 3, 3)
    sns.boxplot(data=df[numeric_cols], palette='pastel')
    plt.xticks(rotation=45)
    plt.title('Numeric Outliers')

    plt.tight_layout()
    plt.show()

# ------------------ Main ------------------
def main():
    with open("config.json", "r") as f:
        config = json.load(f)

    file_path = "diabetes.csv"
    df = load_data(file_path)
    if df is None:
        return

    zero_missing_cols = config.get("zero_as_missing_cols", [])
    clinical_ranges = config.get("clinical_ranges", {})
    outlier_cols = config.get("outlier_columns", [])
    error_weights = config.get("error_weights", {})
    contamination = config.get("contamination", 0.05)

    df, missing_df = missing_value_analysis(df, zero_missing_cols)
    df = outlier_detection(df, outlier_cols)
    df = anomaly_detection_isolation_forest(df, outlier_cols, contamination=contamination)
    df = clinical_range_check(df, clinical_ranges)
    df = pattern_and_format_checks(df)
    df, error_cols = classify_errors_and_score(df, error_weights)

    numeric_cols = ['Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI', 'Age']
    stats_df = statistical_summary(df, numeric_cols)

    overall_quality = generate_reports(df, error_cols, missing_df, stats_df)

    print("\n=== Overall Quality Metrics ===")
    for k, v in overall_quality.items():
        print(f"{k}: {v}")

    print("\n=== Sample Records with Errors ===")
    print(df[['Row_Index'] + numeric_cols + error_cols + ['Quality_Score (%)', 'Error_Log']].head(10))

    visualize_data_quality(df, missing_df, numeric_cols)

if __name__ == "__main__":
    main()