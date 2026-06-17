import json
import os
import sys
from pathlib import Path

sys.path.append('/var/task')

from scripts.analyze_repos import build_headers, fetch_repositories, build_report


def lambda_handler(event, context):
    org = os.environ.get('GITHUB_ORG', '').strip()
    token = os.environ.get('GITHUB_TOKEN', '')
    output_file = os.environ.get('OUTPUT_FILE', '/tmp/repositories.json')
    months = int(os.environ.get('RECENT_MONTHS', '3'))

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

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Repository analysis completed',
            'output_file': str(output_path),
            'summary': report['summary']
        })
    }
