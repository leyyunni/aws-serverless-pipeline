"""
AWS Lambda Function — Federal Spending Data Processor
-------------------------------------------------------
Triggered automatically when a CSV file is uploaded to S3.
Processes the data and saves a summary report back to S3.

Author: Venkata Lakshmi Eyyunni
GitHub: github.com/leyyunni/aws-serverless-pipeline
"""

import json
import boto3
import csv
import io
import os
import logging
from datetime import datetime

# Set up logging — visible in AWS CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# S3 client
s3 = boto3.client("s3")


def lambda_handler(event, context):
    """
    Main entry point — triggered by S3 upload event.

    Args:
        event:   S3 event payload (bucket name + file key)
        context: Lambda runtime context

    Returns:
        dict with statusCode and summary of processing
    """
    logger.info("Lambda triggered — processing S3 event")
    logger.info(json.dumps(event))

    results = []

    for record in event.get("Records", []):

        # ── 1. Extract bucket and file info from the event ──
        bucket = record["s3"]["bucket"]["name"]
        key    = record["s3"]["object"]["key"]

        logger.info(f"Processing file: s3://{bucket}/{key}")

        # ── 2. Only process CSV files ──
        if not key.endswith(".csv"):
            logger.info(f"Skipping non-CSV file: {key}")
            continue

        # ── 3. Download the CSV from S3 ──
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            content  = response["Body"].read().decode("utf-8")
            logger.info(f"Downloaded {len(content)} bytes from S3")
        except Exception as e:
            logger.error(f"Failed to read s3://{bucket}/{key}: {e}")
            raise

        # ── 4. Parse and process the CSV ──
        reader     = csv.DictReader(io.StringIO(content))
        rows       = list(reader)
        total_rows = len(rows)

        logger.info(f"Parsed {total_rows} rows from CSV")

        # ── 5. Analyze the data ──
        summary = analyze_spending_data(rows)

        # ── 6. Build the output report ──
        report = {
            "processed_at":    datetime.utcnow().isoformat() + "Z",
            "source_file":     f"s3://{bucket}/{key}",
            "total_rows":      total_rows,
            "summary":         summary,
            "status":          "success"
        }

        # ── 7. Save the report back to S3 ──
        output_key = key.replace("input/", "output/").replace(".csv", "_report.json")
        save_report(bucket, output_key, report)

        logger.info(f"Report saved to s3://{bucket}/{output_key}")
        results.append(report)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message":        "Processing complete",
            "files_processed": len(results),
            "results":         results
        })
    }


def analyze_spending_data(rows):
    """
    Analyze federal spending CSV data.
    Expects columns: agency, amount, contract_type, fiscal_year
    Handles missing or malformed data gracefully.
    """
    if not rows:
        return {"error": "No data rows found"}

    # ── Total obligation amount ──
    total_amount = 0
    for row in rows:
        try:
            amount = float(str(row.get("amount", "0")).replace(",", "").replace("$", ""))
            total_amount += amount
        except (ValueError, TypeError):
            pass

    # ── Spending by agency ──
    agency_totals = {}
    for row in rows:
        agency = row.get("agency", "Unknown").strip()
        try:
            amount = float(str(row.get("amount", "0")).replace(",", "").replace("$", ""))
        except (ValueError, TypeError):
            amount = 0
        agency_totals[agency] = agency_totals.get(agency, 0) + amount

    top_agencies = sorted(agency_totals.items(), key=lambda x: x[1], reverse=True)[:5]

    # ── Spending by contract type ──
    contract_type_counts = {}
    for row in rows:
        ctype = row.get("contract_type", "Unknown").strip()
        contract_type_counts[ctype] = contract_type_counts.get(ctype, 0) + 1

    # ── Spending by fiscal year ──
    fy_totals = {}
    for row in rows:
        fy = row.get("fiscal_year", "Unknown").strip()
        try:
            amount = float(str(row.get("amount", "0")).replace(",", "").replace("$", ""))
        except (ValueError, TypeError):
            amount = 0
        fy_totals[fy] = fy_totals.get(fy, 0) + amount

    return {
        "total_obligations_usd":  round(total_amount, 2),
        "total_obligations_fmt":  f"${total_amount:,.2f}",
        "top_agencies":           [{"agency": a, "total": round(v, 2)} for a, v in top_agencies],
        "contract_type_breakdown": contract_type_counts,
        "spending_by_fiscal_year": {k: round(v, 2) for k, v in sorted(fy_totals.items())},
        "avg_award_size":          round(total_amount / len(rows), 2) if rows else 0,
    }


def save_report(bucket, key, report):
    """Save JSON report to S3."""
    s3.put_object(
        Bucket      = bucket,
        Key         = key,
        Body        = json.dumps(report, indent=2),
        ContentType = "application/json"
    )
    logger.info(f"Saved report: {len(json.dumps(report))} bytes → s3://{bucket}/{key}")


# ── Local testing ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    """
    Test the Lambda function locally without AWS.
    Creates a sample CSV and runs it through the analyzer.
    """
    print("Running local test...\n")

    # Sample federal spending data
    sample_csv = """agency,amount,contract_type,fiscal_year
Dept of Defense,1800000000,FFP,2024
Dept of Defense,950000000,CPFF,2024
HHS,420000000,CPFF,2024
HHS,180000000,T&M,2023
NASA,890000000,CPFF,2024
DHS,312000000,T&M,2023
VA,215000000,FFP,2023
GSA,178000000,T&M,2022
Dept of Defense,650000000,FFP,2023
HHS,290000000,FFP,2022
"""

    reader = csv.DictReader(io.StringIO(sample_csv))
    rows   = list(reader)
    result = analyze_spending_data(rows)

    print("=== Federal Spending Analysis ===")
    print(f"Total Obligations:  {result['total_obligations_fmt']}")
    print(f"Average Award Size: ${result['avg_award_size']:,.2f}")
    print(f"\nTop Agencies:")
    for a in result["top_agencies"]:
        print(f"  {a['agency']:<30} ${a['total']:>15,.2f}")
    print(f"\nContract Types:")
    for k, v in result["contract_type_breakdown"].items():
        print(f"  {k:<10} {v} contracts")
    print(f"\nBy Fiscal Year:")
    for fy, amt in result["spending_by_fiscal_year"].items():
        print(f"  {fy}: ${amt:>15,.2f}")
    print("\n✅ Local test passed!")
