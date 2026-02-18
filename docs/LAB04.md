# LAB04 - Infrastructure as Code (Terraform + Pulumi)

## 1. Cloud Provider & Infrastructure

### Chosen cloud provider
AWS (EC2 free tier) was chosen because both Terraform and Pulumi AWS providers are stable and well documented.

### Instance and region
- Instance type: `t2.micro`
- Region: `us-east-1`
- Availability zone: `us-east-1a`
- OS image: Ubuntu 22.04 LTS (`jammy` via AMI data source)

### Cost estimate
Expected cost is `$0` if usage stays inside free tier limits.

### Created resources (both Terraform and Pulumi)
- VPC
- Public subnet
- Internet gateway
- Route table + association
- Security group (`22`, `80`, `5000`)
- SSH key pair
- EC2 instance
- Elastic IP (public IP)

## 2. Terraform Implementation

### Terraform version
Target version in code: `>= 1.9.0`.

### Project structure
- `terraform/versions.tf` - Terraform version and AWS provider
- `terraform/variables.tf` - configurable inputs
- `terraform/main.tf` - networking + VM resources
- `terraform/outputs.tf` - public IP and SSH command
- `terraform/terraform.tfvars.example` - safe example values
- `terraform/.tflint.hcl` - lint configuration
- `terraform/github-import/*` - bonus import task

### Key decisions
- Used dedicated Elastic IP to keep stable VM address.
- SSH access is restricted by variable `ssh_allowed_cidr`.
- AMI is selected dynamically (`data "aws_ami"`) to avoid hardcoded IDs.

### Challenges
- In this local environment, `terraform` CLI is not installed, so command execution logs cannot be generated directly here.

### Terminal outputs (to paste after running from your machine)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
terraform output
```

`terraform init` output:
```text
[PASTE YOUR REAL OUTPUT HERE]
```

`terraform plan` output (sanitized):
```text
[PASTE YOUR REAL OUTPUT HERE]
```

`terraform apply` output:
```text
[PASTE YOUR REAL OUTPUT HERE]
```

SSH proof:
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<PUBLIC_IP>
```

SSH session output:
```text
[PASTE YOUR REAL OUTPUT HERE]
```

## 3. Pulumi Implementation

### Pulumi version and language
- Pulumi CLI: `3.x`
- Language: Python

### Project structure
- `pulumi/__main__.py` - equivalent infrastructure definition
- `pulumi/requirements.txt` - `pulumi` and `pulumi-aws`
- `pulumi/Pulumi.yaml` - project metadata
- `pulumi/Pulumi.dev.yaml.example` - stack config template

### How code differs from Terraform
- Terraform uses declarative HCL blocks.
- Pulumi uses Python objects, regular variables, and language-native composition.
- In Pulumi, outputs are exported directly with `pulumi.export`.

### Advantages discovered
- Pulumi gives full Python expressiveness and easier code reuse.
- Terraform has simpler structure for straightforward infrastructure and clearer `plan` UX.

### Challenges
- In this local environment, `pulumi` CLI is not installed, so command execution logs cannot be generated directly here.

### Terminal outputs (to paste after running from your machine)

```bash
cd pulumi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

pulumi login
pulumi stack init dev
cp Pulumi.dev.yaml.example Pulumi.dev.yaml
pulumi config set aws:region us-east-1
pulumi config set lab04-iac:sshAllowedCidr "<YOUR_PUBLIC_IP>/32"
pulumi config set lab04-iac:sshPublicKey "$(cat ~/.ssh/id_ed25519.pub)"

pulumi preview
pulumi up
pulumi stack output
```

`pulumi preview` output:
```text
[PASTE YOUR REAL OUTPUT HERE]
```

`pulumi up` output:
```text
[PASTE YOUR REAL OUTPUT HERE]
```

SSH proof:
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<PULUMI_PUBLIC_IP>
```

SSH session output:
```text
[PASTE YOUR REAL OUTPUT HERE]
```

## 4. Terraform vs Pulumi Comparison

### Ease of learning
Terraform is easier for first contact because HCL is minimal and focused only on infrastructure. Pulumi is easier if you already write Python every day and want to reuse programming patterns.

### Code readability
For simple one-VM scenarios, Terraform is shorter and easier to scan. For growing logic with conditions and reusable abstractions, Pulumi Python becomes more readable.

### Debugging
Terraform gives predictable `plan` and clear resource diffs before apply, which helps beginners. Pulumi debugging can be better for developers because it uses familiar language stack traces.

### Documentation
Terraform has a larger ecosystem and usually more examples per provider/resource. Pulumi docs are good but community examples are smaller.

### Use case preference
Use Terraform for standard platform IaC with minimal custom logic and team-wide readability. Use Pulumi when infrastructure needs complex logic, reusable code modules, or strict integration with existing Python/TypeScript tooling.

## 5. Lab 5 Preparation & Cleanup

### VM plan for Lab 5
- Keep VM for Lab 5: **Yes**
- Preferred VM: **Pulumi-created VM**
- Reason: easier iterative changes in Python code

### Cleanup status
- Terraform resources: must be destroyed before switching to Pulumi
- Pulumi resources: keep one VM running for Lab 5

Commands:
```bash
cd terraform
terraform destroy

cd ../pulumi
pulumi stack output publicIp
```

Add final proof after execution:
```text
[PASTE DESTROY / STATUS OUTPUT HERE]
```

## Bonus Part 1 - IaC CI/CD

### Workflow implementation
File: `.github/workflows/terraform-ci.yml`

What it does:
- Triggers on pull requests only when `terraform/**` or workflow file changes
- Runs `terraform fmt -check -recursive`
- Runs `terraform init -backend=false`
- Runs `terraform validate`
- Runs `tflint --init` and `tflint`
- Validates both directories with matrix:
  - `terraform`
  - `terraform/github-import`

### How to prove
1. Open PR with only Terraform changes and attach successful workflow screenshot.
2. Open PR with non-Terraform change and show workflow is not triggered.

## Bonus Part 2 - GitHub Repository Import

### Config location
- `terraform/github-import/main.tf`
- `terraform/github-import/variables.tf`

### Import process
```bash
cd terraform/github-import
cp terraform.tfvars.example terraform.tfvars
export GITHUB_TOKEN="<YOUR_TOKEN>"

terraform init
terraform validate
terraform import -var-file=terraform.tfvars github_repository.course_repo DevOps-Core-Course
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

Import output:
```text
[PASTE YOUR REAL OUTPUT HERE]
```

### Why import matters
Import allows existing manually-created resources to be moved under IaC without recreation. That gives version control, reviewable changes, and reproducible configuration management.
