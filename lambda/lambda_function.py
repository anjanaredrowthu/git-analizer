import json
import os
import sys
from pathlib import Path

import boto3

sys.path.append('/var/task')

from scripts.analyze_repos import build_headers, fetch_repositories, build_report


S3_CLIENT = boto3.client('s3')


def lambda_handler(event, context):
    org = os.environ.get('GITHUB_ORG', '').strip()
    token = os.environ.get('GITHUB_TOKEN', '')
    output_file = os.environ.get('OUTPUT_FILE', '/tmp/repositories.json')
    months = int(os.environ.get('RECENT_MONTHS', '3'))
    s3_enabled = os.environ.get('S3_OUTPUT_ENABLED', 'true').lower() == 'true'
    bucket_name = os.environ.get('S3_BUCKET_NAME', '').strip()
    bucket_key = os.environ.get('S3_BUCKET_KEY', 'reports/repositories.json')

    if not org:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'GITHUB_ORG is required'})
        }

    headers = build_headers(token)
    repositories = fetch_repositories(org, headers)
    report = build_report(org, repositories, months, headers)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as file:
        json.dump(report, file, indent=2, sort_keys=True)
        file.write('\n')

    s3_upload_uri = None
    if s3_enabled and bucket_name:
        S3_CLIENT.upload_file(str(output_path), bucket_name, bucket_key)
        s3_upload_uri = f"s3://{bucket_name}/{bucket_key}"

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Repository analysis completed',
            'output_file': str(output_path),
            's3_uri': s3_upload_uri,
            'summary': report['summary']
        })
    }
