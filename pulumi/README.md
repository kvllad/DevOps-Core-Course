# Pulumi: Lab 04 Infrastructure (AWS, Python)

## What this creates
- VPC + public subnet
- Internet gateway + route table
- Security group with ports `22`, `80`, `5000`
- EC2 VM (`t2.micro` by default)
- Elastic IP

## Prerequisites
1. Pulumi CLI `3.x`
2. Python `3.11+`
3. AWS credentials configured (`aws configure` or env vars)

## Quick start
```bash
cd pulumi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

pulumi login
pulumi stack init dev
cp Pulumi.dev.yaml.example Pulumi.dev.yaml

pulumi config set aws:region us-east-1
pulumi config set lab04-iac:sshAllowedCidr "YOUR_PUBLIC_IP/32"
pulumi config set lab04-iac:sshPublicKey "$(cat ~/.ssh/id_ed25519.pub)"

pulumi preview
pulumi up
```

## Connect to VM
```bash
pulumi stack output sshCommand
```

## Destroy resources
```bash
pulumi destroy
```

## Notes
- Do not commit `Pulumi.<stack>.yaml` if it contains secrets.
- Keep VM only if needed for Lab 5.
