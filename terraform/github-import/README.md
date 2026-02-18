# Terraform GitHub Import (Lab 04 Bonus)

## Prerequisites
1. Terraform `1.9+`
2. GitHub token in env var:
```bash
export GITHUB_TOKEN="ghp_xxx"
```
3. Access to the target repository

## Initialize
```bash
cd terraform/github-import
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt
terraform validate
```

## Import existing repository
```bash
terraform import -var-file=terraform.tfvars github_repository.course_repo DevOps-Core-Course
```

## Check drift
```bash
terraform plan -var-file=terraform.tfvars
```

## Apply managed settings
```bash
terraform apply -var-file=terraform.tfvars
```

## Why this matters
Import lets you move already-created resources under IaC control without recreating them.
