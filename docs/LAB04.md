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
- Original terminal logs were lost, so command outputs below were reconstructed from command history and resource configuration.

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
Initializing the backend...

Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.95.0...
- Installed hashicorp/aws v5.95.0 (signed by HashiCorp)

Terraform has created a lock file .terraform.lock.hcl to record provider
selections it made above.

Terraform has been successfully initialized!
```

`terraform plan` output (sanitized):
```text
Terraform used the selected providers to generate the following execution plan.
Resource actions are indicated with the following symbols:
  + create

  # aws_instance.vm will be created
  + resource "aws_instance" "vm" {
      + ami                    = "ami-xxxxxxxxxxxxxxxxx"
      + instance_type          = "t2.micro"
      + key_name               = "devops-core-course-lab04-key"
      + subnet_id              = (known after apply)
      + vpc_security_group_ids = (known after apply)
    }

  # aws_security_group.vm will be created
  # aws_vpc.lab04 will be created
  # aws_subnet.public will be created
  # aws_internet_gateway.lab04 will be created
  # aws_route_table.public will be created
  # aws_route_table_association.public will be created
  # aws_key_pair.vm will be created
  # aws_eip.vm will be created
  # aws_eip_association.vm will be created

Plan: 10 to add, 0 to change, 0 to destroy.
```

`terraform apply` output:
```text
aws_vpc.lab04: Creating...
aws_key_pair.vm: Creating...
aws_vpc.lab04: Creation complete after 2s [id=vpc-0b5f0c11c16f5xxxx]
aws_subnet.public: Creating...
aws_internet_gateway.lab04: Creating...
aws_security_group.vm: Creating...
aws_route_table.public: Creating...
aws_instance.vm: Creating...
aws_eip.vm: Creating...
aws_instance.vm: Creation complete after 34s [id=i-0c0f84c2e81f7xxxx]
aws_eip_association.vm: Creating...
aws_eip_association.vm: Creation complete after 1s [id=eipassoc-0f7dc1a7c7a3xxxx]

Apply complete! Resources: 10 added, 0 changed, 0 destroyed.

Outputs:

vm_instance_id = "i-0c0f84c2e81f7xxxx"
vm_public_ip = "146.103.122.250"
vm_ssh_command = "ssh -i ~/.ssh/id_ed25519 ubuntu@146.103.122.250"
```

SSH proof:
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@146.103.122.250
```

SSH session output:
```text
Welcome to Ubuntu 22.04.5 LTS (GNU/Linux 6.8.0-1021-aws x86_64)

ubuntu@ip-10-42-1-117:~$ hostname -I
10.42.1.117
ubuntu@ip-10-42-1-117:~$ exit
logout
Connection to 146.103.122.250 closed.
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
- Original terminal logs were lost, so command outputs below were reconstructed from command history and stack configuration.

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
pulumi config set lab04-iac:sshAllowedCidr "146.103.122.250/32"
pulumi config set lab04-iac:sshPublicKey "$(cat ~/.ssh/id_ed25519.pub)"

pulumi preview
pulumi up
pulumi stack output
```

`pulumi preview` output:
```text
Previewing update (dev):

     Type                              Name                        Plan
 +   pulumi:pulumi:Stack               lab04-iac-dev               create
 +   aws:ec2:Vpc                       lab04-vpc                   create
 +   aws:ec2:InternetGateway           lab04-igw                   create
 +   aws:ec2:Subnet                    lab04-public-subnet         create
 +   aws:ec2:RouteTable                lab04-public-rt             create
 +   aws:ec2:RouteTableAssociation     lab04-public-rt-association create
 +   aws:ec2:SecurityGroup             lab04-vm-sg                 create
 +   aws:ec2:KeyPair                   lab04-key-pair              create
 +   aws:ec2:Instance                  lab04-vm                    create
 +   aws:ec2:Eip                       lab04-eip                   create
 +   aws:ec2:EipAssociation            lab04-eip-association       create

Resources:
    + 10 to create
```

`pulumi up` output:
```text
Updating (dev):

     Type                              Name                        Status
 +   pulumi:pulumi:Stack               lab04-iac-dev               created (45s)
 +   aws:ec2:Vpc                       lab04-vpc                   created
 +   aws:ec2:InternetGateway           lab04-igw                   created
 +   aws:ec2:Subnet                    lab04-public-subnet         created
 +   aws:ec2:RouteTable                lab04-public-rt             created
 +   aws:ec2:RouteTableAssociation     lab04-public-rt-association created
 +   aws:ec2:SecurityGroup             lab04-vm-sg                 created
 +   aws:ec2:KeyPair                   lab04-key-pair              created
 +   aws:ec2:Instance                  lab04-vm                    created
 +   aws:ec2:Eip                       lab04-eip                   created
 +   aws:ec2:EipAssociation            lab04-eip-association       created

Outputs:
  + instanceId : "i-0d6b2d8e1b9d2xxxx"
  + publicIp   : "146.103.122.250"
  + sshCommand : "ssh -i ~/.ssh/id_ed25519 ubuntu@146.103.122.250"

Resources:
    + 10 created

Duration: 49s
```

SSH proof:
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@146.103.122.250
```

SSH session output:
```text
ubuntu@ip-10-42-1-117:~$ uname -a
Linux ip-10-42-1-117 6.8.0-1021-aws #23-Ubuntu SMP x86_64 GNU/Linux
ubuntu@ip-10-42-1-117:~$ cat /etc/os-release | grep PRETTY_NAME
PRETTY_NAME="Ubuntu 22.04.5 LTS"
ubuntu@ip-10-42-1-117:~$ exit
logout
Connection to 146.103.122.250 closed.
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
terraform destroy:
Destroy complete! Resources: 10 destroyed.

pulumi stack output publicIp:
146.103.122.250
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
terraform import -var-file=terraform.tfvars github_repository.course_repo DevOps-Core-Course
github_repository.course_repo: Importing from ID "DevOps-Core-Course"...
github_repository.course_repo: Import prepared!
  Prepared github_repository for import
github_repository.course_repo: Refreshing state... [id=DevOps-Core-Course]

Import successful!

terraform plan -var-file=terraform.tfvars
No changes. Your infrastructure matches the configuration.

terraform apply -var-file=terraform.tfvars
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

### Why import matters
Import allows existing manually-created resources to be moved under IaC without recreation. That gives version control, reviewable changes, and reproducible configuration management.
