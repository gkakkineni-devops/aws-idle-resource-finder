# aws-idle-resource-finder

![ci](https://github.com/gkakkineni-devops/aws-idle-resource-finder/actions/workflows/ci.yml/badge.svg)

A small AWS Lambda function that looks through one region for resources that cost money and do nothing, then writes a JSON report to S3. Terraform deploys it and EventBridge runs it once a week.

It only reads. It never deletes or changes anything in your account. That is on purpose: a tool that tells you about waste is safe to run anywhere, and a tool that deletes things needs a lot more care.

## What it finds

| Finding | What it means | Estimated cost |
|---|---|---|
| Unattached volume | An EBS volume that isn't attached to anything | size in GB x $0.08 a month |
| Unassociated Elastic IP | A public IP that points at nothing | $3.65 a month |
| Old snapshot | One of your snapshots older than 90 days | size in GB x $0.05 a month, an upper bound |
| Untagged instance | An EC2 instance missing an `owner` or `project` tag | none, it is just a flag |

The prices are rough us-east-1 list prices that I typed in as constants at the top of `src/finder/checks.py`. Treat the totals as a way to rank problems, not as accounting.

## How it fits together

```
EventBridge (weekly)  ->  Lambda  ->  EC2 describe calls (read only)
                            |
                            |-> S3 (the JSON report)
                            '-> CloudWatch Logs
```

- `src/finder/checks.py` holds the rules. Nothing in it talks to AWS. Each function takes plain data and returns findings.
- `src/finder/aws.py` is the only file that talks to AWS. Every function takes the client as an argument, so the tests can pass in a fake one.
- `src/finder/scan.py` reads the settings, runs every check and builds the report.
- `src/finder/report.py` turns the findings into the report and picks the S3 key.
- `src/finder/handler.py` is what Lambda calls. `src/finder/__main__.py` runs the same scan from a laptop.
- `terraform/` creates the function, a role that can only do what it needs, a private encrypted bucket, a log group and the weekly schedule.

## What a report looks like

The ids here are made up.

```json
{
  "generated_at": "2026-11-09T13:00:00+00:00",
  "region": "us-east-1",
  "finding_count": 4,
  "estimated_monthly_waste_usd": 14.15,
  "by_kind": {
    "old_snapshot": 1,
    "unassociated_ip": 1,
    "unattached_volume": 1,
    "untagged_instance": 1
  },
  "findings": [
    {
      "kind": "unattached_volume",
      "resource_id": "vol-0a1b2c3d4e5f60001",
      "reason": "100 GB volume is not attached to any instance",
      "monthly_cost_usd": 8.0
    }
  ]
}
```

Findings are sorted with the most expensive first. The real report lists all four. I cut it down here to keep the page short.

## Run it on your laptop

You need Python 3.12 or newer.

```
python -m venv .venv
source .venv/bin/activate        # Git Bash on Windows: source .venv/Scripts/activate
pip install -r requirements-dev.txt
pytest
```

To scan a real account, sign in with the AWS CLI first, then:

```
PYTHONPATH=src python -m finder --region us-east-1
```

That only reads and prints the report. Options: `--max-snapshot-age-days` (default 90) and `--required-tags` (default `owner,project`).

## Deploy it

You need Terraform 1.6 or newer and AWS credentials for an account you own.

```
cd terraform
terraform init
terraform plan
terraform apply
```

Read the plan before you apply it. Then run the function once by hand and look at the report:

```
aws lambda invoke --function-name idle-resource-finder --region us-east-1 out.json
aws s3 ls s3://$(terraform output -raw report_bucket)/reports/ --recursive
```

`terraform destroy` removes everything, including the reports. The things you can change are in `terraform/variables.tf`: the region, the name, the schedule, the snapshot age, the required tags and how long logs and reports are kept. Terraform keeps its state in a local file that is in `.gitignore`. Never commit it.

## Decisions

- **Read only.** The role can describe four kinds of EC2 resources, write to one folder of one bucket and write to one log group. It has no delete or change permission anywhere. The describe calls use `*` as the resource because AWS doesn't let you narrow them, and there is a comment in `iam.tf` saying so.
- **No AWS inside the rules.** Because the checks take plain data, the tests build that data by hand. The snapshot check takes the current time as an argument for the same reason, so a test can pick any date.
- **Logs and reports expire.** Terraform creates the log group so it can set a retention period, otherwise Lambda keeps the logs forever. Reports are deleted from the bucket after 90 days.
- **Security scan with two accepted findings.** Trivy runs on the Terraform in CI. `.trivyignore` accepts two findings, each with the reason written next to it: the bucket uses S3's own encryption instead of a customer managed KMS key (which costs money every month), and the EC2 read statement has to use `*`.
- **Local Terraform state.** This is a solo project. A team would keep state in S3 with locking.

## Limits

- One region per deployment.
- It doesn't look at CPU use, so an instance that is attached but sitting idle is not found.
- The prices are constants. The same price is used for every volume type, and snapshots are counted at full size even though they are incremental, so real bills are often lower.
- A snapshot that backs an AMI shows up as old, even though you can't delete it while the image exists.
- The Lambda timeout is 60 seconds. An account with a very large number of resources may need more.
- It reports waste. Nothing acts on it.

## What I've actually run

- [x] Unit tests and lint pass in CI (27 tests, one of them against moto, a pretend AWS)
- [x] The Terraform passes in CI: a Trivy scan, `terraform fmt`, `init` and `validate` against the real AWS provider, and tflint
- [ ] Ran the finder from my laptop against a real AWS account
- [ ] Deployed it with Terraform to a real AWS account and invoked the function
- [ ] Destroyed everything afterwards

Nothing here has touched a real AWS account yet, so the report you see above comes from the tests and not from a live scan.

## License

MIT
