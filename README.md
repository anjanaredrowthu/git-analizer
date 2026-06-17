# git-analizer

This project retrieves repositories from a GitHub organization or user account, filters them by:
- GitHub Actions enabled
- more than 5 contributors
- updated within the last N months

The script writes a JSON report to `reports/repositories.json` by default and prints a summary.

## 1. Run locally

### Prerequisites
- Python 3.11+
- A GitHub token if the organization is private or API rate limits are a concern

### Steps
```bash
python -m pip install -r requirements.txt
python scripts/analyze_repos.py --org <org-or-user>
```

Optional arguments:
```bash
python scripts/analyze_repos.py \
  --org <org-or-user> \
  --token <github-token> \
  --output reports/repositories.json \
  --months 3
```

## 2. GitHub Actions automation

The workflow in [.github/workflows/analyze_repos.yml](.github/workflows/analyze_repos.yml) runs weekly and can also be triggered manually.

### Recommended repository settings
- Set `GH_API_TOKEN` (or `GITHUB_TOKEN`) as a repository or organization secret
- Optionally set `GITHUB_ORG` as a repository variable if you want to avoid passing the org manually

### Workflow schedule
The workflow runs every Sunday at 03:00 UTC.

## 3. AWS Lambda + Terraform deployment

The repository also contains Terraform infrastructure for deploying the analyzer to AWS Lambda with a scheduled trigger.

### Steps
```bash
bash lambda/build_package.sh
cp infra/variables.tfvars.example infra/terraform.tfvars
cd infra
terraform init
terraform plan
terraform apply
```

### Output behavior
- The Lambda writes the JSON report to `/tmp/repositories.json`
- The Terraform setup also uploads that file to an S3 bucket created by the infrastructure at `s3://<bucket-name>/reports/repositories.json`
- S3 output is enabled by default in the Terraform configuration

See [infra/README.md](infra/README.md) for more details.

## 4. Validate the setup

You can run the local validation checks with:
```bash
python -m compileall scripts/analyze_repos.py lambda/lambda_function.py
```

There is also a CI workflow in [.github/workflows/terraform_validate.yml](.github/workflows/terraform_validate.yml) that validates the Terraform config and Lambda packaging.
