"""Command-line entry point for DataReporter."""

from datareporter.core.scanner import scan_folders
from datareporter.core.reporter import generate_reports


def main():
    import argparse

    parser = argparse.ArgumentParser(description="DataReporter CLI")
    parser.add_argument("folders", nargs="+", help="Folders to scan for Nexus HDF5 files")
    parser.add_argument("--output", "-o", default="reports", help="Output directory for reports")
    parser.add_argument("--format", choices=["pdf", "md", "csv", "all"], default="all", help="Report format")
    args = parser.parse_args()

    records = scan_folders(args.folders)
    generate_reports(records, args.output, fmt=args.format)


if __name__ == "__main__":
    main()
