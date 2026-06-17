# Lambda deployment guide

This folder contains the AWS Lambda entry point for the repository analyzer.

## Execution steps

1. Install dependencies for the project:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Build the Lambda package:
   ```bash
   bash lambda/build_package.sh
   ```
3. Copy the Terraform variable example file and update it:
   ```bash
   cp infra/variables.tfvars.example infra/terraform.tfvars
   ```
4. Deploy the infrastructure:
   ```bash
   cd infra
   terraform init
   terraform apply
   ```
5. After deployment, the Lambda will run the analyzer and store the JSON output in:
   - `/tmp/repositories.json` inside the Lambda runtime
   - `s3://<bucket-name>/reports/repositories.json` because S3 output is enabled by default in the Terraform configuration

## Notes
- The Lambda handler is defined in [lambda_function.py](lambda_function.py).
- The analyzer logic is in [../scripts/analyze_repos.py](../scripts/analyze_repos.py).
- The Terraform setup for the Lambda and scheduler is in [../infra/main.tf](../infra/main.tf).
