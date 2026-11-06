ORION 6.1 — Real-World Dataset Analysis Demo

Overview

This demo documents an analysis performed by ORION 6.1 on a 50,000-record sample of New York City's 311 Service Requests dataset.

The purpose is to demonstrate ORION's dataset-inspection capabilities on a real public dataset.

Project: ORION
Version: 6.1
Developer: SK Nadeem
Dataset: NYC 311 Service Requests
Format: CSV
Sample size: 50,000 rows × 44 columns
File size: 44,679,417 bytes (~42.6 MiB)

Dataset Source

The dataset is published through NYC Open Data:

https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9/data

This demonstration uses a 50,000-record sample ordered by most recent creation date. It is not an analysis of the entire dataset.

Reproducing the Demo

Clone the repository:

git clone https://github.com/nadeem677n/ORION.git
cd ORION

Download the 50,000-record sample:

mkdir -p data

curl -L --fail --show-error \
"https://data.cityofnewyork.us/resource/erm2-nwe9.csv?$limit=50000&$order=created_date%20DESC" \
-o data/nyc_311_sample.csv

Run ORION:

python3 orion.py data/nyc_311_sample.csv

ORION generates JSON and HTML analysis reports.

Actual Analysis Results

Metric| Result
Rows processed| 50,000
Columns inspected| 44
Total cells| 2,200,000
Missing cells| 600,325
Duplicate rows| 0
Malformed records| 0
Empty rows| 0
Processing time| 135.2164 seconds
Processing throughput| 369.78 rows/second

These are results from this specific run and environment, not universal performance benchmarks.

Findings

1. Missing Values

ORION detected 600,325 missing cells across the dataset.

Missing values are not automatically data errors. Some fields may only apply to particular complaint categories or circumstances.

For example, "closed_date" contained 16,193 missing values in this sample.

2. Duplicate Rows

ORION detected zero duplicate rows in the 50,000-record sample.

3. Column Analysis

ORION identified several structural characteristics, including:

- Constant columns.
- Duplicate columns.
- Columns containing mixed data types.
- Missing-value distributions.
- Numeric statistics.

In this run, "facility_type" and "park_facility_name" were identified as constant columns. "park_borough" was identified as matching "borough", and "bridge_highway_name" was identified as containing mixed data types.

4. Numeric Analysis

ORION calculates numeric statistics, including:

- Count
- Mean
- Minimum and maximum
- Population variance
- Standard deviation

It also performs IQR-based outlier detection using a bounded sample.

5. Frequent Values

ORION tracks frequently occurring values to help inspect categorical columns.

Important: Frequent-value tracking is approximate and is not guaranteed to return exact frequencies.

Limitations

This demonstration should be interpreted with the following limitations:

- It uses a 50,000-record sample, not the complete NYC 311 dataset.
- Frequent-value tracking is approximate.
- IQR outlier detection is sample-based, with a maximum sample size of 10,000.
- Missing values do not necessarily indicate incorrect data.
- ORION's CodeScan and dataset checks are inspection tools, not guarantees that data or code is error-free.
- Processing speed depends on the device, Python environment, file structure, and system conditions.

Conclusion

This experiment demonstrates ORION 6.1 inspecting a real-world dataset containing 50,000 records and 44 columns.

The run examined 2.2 million cells and reported missing values, duplicate rows, record structure, column characteristics, numeric statistics, and other dataset observations.

ORION is an independent, non-AI algorithmic project focused on dataset analysis and Python code inspection.

Developed by SK Nadeem.
