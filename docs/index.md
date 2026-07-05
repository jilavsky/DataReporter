# DataReporter Documentation

## Overview

DataReporter scans directories for Nexus HDF5 files, extracts metadata, generates plots (JPG) and produces reports in PDF, Markdown, or CSV.

## Installation

```bash
pip install datareporter
```

## Usage

```bash
python -m datareporter /path/to/data
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
