"""CSV export for filtered analytics."""

import csv
from io import StringIO


def build_analytics_csv(summary, category_totals, monthly_totals):
    """Export the same totals used by the dashboard."""
    output = StringIO(newline="")
    writer = csv.writer(output)

    writer.writerow(["Section", "Label", "Emissions (kg CO2e)", "Record count"])

    writer.writerow([
        "Summary",
        "Total emissions",
        f"{summary['total_emissions']:.2f}",
        summary["record_count"],
    ])

    for item in category_totals:
        writer.writerow([
            "Category",
            safe_csv_label(item["category"]),
            f"{item['total_emissions']:.2f}",
            "",
        ])

    for item in monthly_totals:
        writer.writerow([
            "Month",
            item["month"],
            f"{item['total_emissions']:.2f}",
            "",
        ])

    return output.getvalue()


def safe_csv_label(value):
    """Keep category labels as text when opened in a spreadsheet."""
    text = str(value)

    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text

    return text