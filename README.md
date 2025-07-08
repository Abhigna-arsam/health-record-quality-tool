# 🩺 Health Record Quality Tool

A modular Python-based tool for auditing Electronic Health Records (EHR) datasets to detect **missing values**, **outliers**, **range violations**, and **format inconsistencies**, and to generate detailed **quality reports**.

---

## 📌 Problem Statement

> Build a tool that analyzes EHR data for **completeness**, **consistency**, and **potential errors**.

This tool:
- Detects missing data (including zeros as missing)
- Performs outlier detection (IQR and Isolation Forest)
- Validates clinical ranges
- Checks format and pattern issues
- Assigns quality scores and classifies errors
- Generates structured reports with visualizations

---

## ⚙️ Features

- Modular pipeline  
- Configurable via `config.json`  
- AI/ML-based anomaly detection  
- Clinical validation rules  
- Completeness & quality scoring  
- Error logs with actual data values  
- Visual data quality dashboard  

---

