# AWS Serverless Pipeline — Federal Spending Data Processor

An event-driven serverless pipeline that automatically processes federal spending CSV files uploaded to S3, analyzes the data, and saves structured JSON reports back to S3.

**Author:** Venkata Lakshmi Eyyunni  
**GitHub:** [github.com/leyyunni/aws-serverless-pipeline](https://github.com/leyyunni/aws-serverless-pipeline)

---

## Architecture

```
         ┌─────────────────────────────────────────────────────┐
         │                    AWS Account                       │
         │                                                      │
         │   S3 Bucket                                          │
         │   ┌──────────────────┐    S3 Event        ┌───────┐ │
  CSV ──►│   │  input/*.csv     │ ──────────────────► │       │ │
  upload │   └──────────────────┘                     │  λ   │ │
         │                                            │       │ │
         │   ┌──────────────────┐    PutObject        │Lambda │ │
  JSON ◄─│   │  output/*_report │ ◄────────────────── │       │ │
  report │   └──────────────────┘                     └───────┘ │
         │                                                ▼      │
         │                                         CloudWatch    │
         │                                           Logs        │
         └─────────────────────────────────────────────────────┘
```

1. A CSV file is uploaded to the `input/` prefix of the S3 bucket
2. S3 fires an event that invokes the Lambda function
3. Lambda downloads, parses, and analyzes the CSV
4. A JSON summary report is saved to the `output/` prefix
5. All logs stream to CloudWatch

---

## Project Structure

```
aws-serverless-pipeline/
├── lambda/
│   └── handler.py              # Lambda function + local test runner
├── terraform/
│   ├── main.tf                 # S3, Lambda, IAM, CloudWatch resources
│   └── variables.tf            # Configurable inputs
├── .github/
│   └── workflows/
│       └── deploy.yml          # CI/CD: test → package → plan/apply
└── README.md
```

---

## CSV Format

The Lambda expects CSV files with these columns:

| Column          | Type   | Example              |
|-----------------|--------|----------------------|
| `agency`        | string | `Dept of Defense`    |
| `amount`        | number | `1800000000`         |
| `contract_type` | string | `FFP`, `CPFF`, `T&M` |
| `fiscal_year`   | string | `2024`               |

Missing or malformed values are handled gracefully (defaulted to 0 / "Unknown").

---

## Output Report

Each processed CSV produces a JSON report at `output/<filename>_report.json`:

```json
{
  "processed_at": "2024-01-15T10:30:00Z",
  "source_file": "s3://my-bucket/input/spending.csv",
  "total_rows": 10,
  "status": "success",
  "summary": {
    "total_obligations_usd": 5885000000.0,
    "total_obligations_fmt": "$5,885,000,000.00",
    "avg_award_size": 588500000.0,
    "top_agencies": [
      { "agency": "Dept of Defense", "total": 3400000000.0 }
    ],
    "contract_type_breakdown": { "FFP": 4, "CPFF": 3, "T&M": 3 },
    "spending_by_fiscal_year": { "2022": 468000000.0, "2024": 4060000000.0 }
  }
}
```

---

## Local Development

**Prerequisites:** Python 3.12+, `pip`

```bash
# Install dependencies
pip install boto3

# Run the built-in local test (no AWS needed)
python3 lambda/handler.py
```

Expected output:
```
=== Federal Spending Analysis ===
Total Obligations:  $5,885,000,000.00
Average Award Size: $588,500,000.00
...
✅ Local test passed!
```

---

## Deploying with Terraform

**Prerequisites:** [Terraform >= 1.3](https://developer.hashicorp.com/terraform/install), AWS CLI configured

```bash
# 1. Package the Lambda
cd lambda && zip -r handler.zip handler.py && cd ..

# 2. Initialize Terraform
cd terraform && terraform init

# 3. Preview changes
terraform plan

# 4. Deploy
terraform apply
```

Terraform will output the S3 bucket name and Lambda function name.

---

## CI/CD with GitHub Actions

The workflow in `.github/workflows/deploy.yml` runs automatically:

| Trigger        | Jobs run                          |
|----------------|-----------------------------------|
| Pull request   | Test → Package → Terraform Plan   |
| Push to `main` | Test → Package → Terraform Apply  |

### Required GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret                  | Description                  |
|-------------------------|------------------------------|
| `AWS_ACCESS_KEY_ID`     | IAM user access key          |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key          |

The IAM user needs permissions for: S3, Lambda, IAM, CloudWatch Logs.

### Required GitHub Environment

Create a `production` environment under **Settings → Environments** to gate Terraform apply behind a manual approval step (optional but recommended).

---

## Infrastructure Overview

| Resource              | Details                                        |
|-----------------------|------------------------------------------------|
| S3 Bucket             | Versioned, AES-256 encrypted, no public access |
| Lambda Runtime        | Python 3.12, 256 MB RAM, 60s timeout           |
| Lambda Trigger        | `s3:ObjectCreated:*` on `input/*.csv`          |
| IAM Role              | Least-privilege: S3 bucket + CloudWatch only   |
| CloudWatch Log Group  | 14-day retention                               |

---

## License

MIT
