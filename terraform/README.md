# Terraform: Lab 04 Infrastructure (AWS)

## What this creates
- VPC + public subnet
- Internet gateway + route table
- Security group with ports `22`, `80`, `5000`
- EC2 VM (`t2.micro` by default)
- Elastic IP

## Prerequisites
1. Terraform `1.9+`
2. AWS account with permissions for VPC/EC2/EIP/KeyPair
3. SSH public key file (default `~/.ssh/id_ed25519.pub`)
4. AWS credentials configured (`aws configure` or env vars)

## Quick start
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars (especially ssh_allowed_cidr)
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

## Connect to VM
```bash
terraform output vm_ssh_command
```

## Destroy resources
```bash
terraform destroy
```

## Notes
- Do not commit `terraform.tfvars` and state files.
- Keep the VM only if you plan to use it in Lab 5.
