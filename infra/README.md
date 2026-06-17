# Terraform deployment notes

## Prerequisites
- AWS CLI configured with credentials
- Terraform installed
- A GitHub token (or repo secret) with permission to read repository metadata

## Steps
1. Copy the example variables file and update values:
   ```bash
   cp infra/variables.tfvars.example infra/terraform.tfvars
   ```
2. Run:
   ```bash
   cd infra
   terraform init
   terraform plan
   terraform apply
   ```

## S3 output
The Lambda uploads the generated JSON report to an S3 bucket created by Terraform. The output object path is:

- `s3://<bucket-name>/reports/repositories.json`

## Lambda packaging behavior
The Terraform config now runs [lambda/build_package.sh](lambda/build_package.sh) automatically before creating the Lambda package, so you do not need to build the ZIP manually first.
