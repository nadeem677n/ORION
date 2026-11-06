<div align="center">

# ORION

### Open Research & Intelligent Observation Network

**A Non-AI Algorithmic Engine for Real-World Data Analysis**

Built by **SK Nadeem**

[![Python](https://img.shields.io/badge/Python-3.14+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-6.1-purple)]()

</div>

---

## About ORION

ORION is an independent, non-AI algorithmic research project designed to inspect real-world datasets and Python source code.

It focuses on identifying data-quality issues, statistical patterns, structural inconsistencies, and selected code-level risks through traditional programming and algorithmic methods.

ORION does not require a generative AI model.

## Features

### Dataset Analysis
- CSV, TSV, JSON and JSONL support
- Missing-value detection
- Data-type classification
- Mixed-type and constant-column detection
- Duplicate-row detection
- Duplicate-column detection
- Numeric statistical analysis
- IQR-based outlier inspection using sampling
- Approximate frequent-value tracking
- JSON and HTML report generation
- Smart Action Guide

### Python Code Inspection
- Python syntax validation
- AST-based code inspection
- Detection of selected risky function calls
- TODO/FIXME comment detection
- Basic pickle-deserialization checks

## Installation

Clone the repository:

```bash
git clone https://github.com/nadeem677n/ORION.git
cd ORION

python3 orion.py
```

## Usage

Interactive menu:

```bash
python3 orion.py
```

Analyse a dataset:

```bash
python3 orion.py dataset.csv
```

Inspect Python code:

```bash
python3 orion.py script.py
```

## Research Notes

ORION is an evolving open-source project.

Some analyses use sampling and approximate algorithms. Outlier results are sample-based, frequent-value counts are approximate, and CodeScan is not a complete security audit.

Results should be independently verified before making important decisions.

## Project Vision

The goal is to research, develop, and improve useful non-AI algorithms for practical data analysis and software inspection.

## Founder

**SK Nadeem**

Independent Developer & Founder of ORION

---

<div align="center">

**ORION — Independent Research. Algorithmic Thinking. Real-World Data.**

</div>
