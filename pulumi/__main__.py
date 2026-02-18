import pulumi
import pulumi_aws as aws

config = pulumi.Config()

project_name = config.get("projectName") or "devops-core-course-lab04"
environment = config.get("environment") or "dev"
availability_zone = config.get("availabilityZone") or "us-east-1a"
vpc_cidr = config.get("vpcCidr") or "10.42.0.0/16"
public_subnet_cidr = config.get("publicSubnetCidr") or "10.42.1.0/24"
instance_type = config.get("instanceType") or "t2.micro"
instance_user = config.get("instanceUser") or "ubuntu"
ssh_private_key_path = config.get("sshPrivateKeyPath") or "~/.ssh/id_ed25519"
ssh_allowed_cidr = config.get("sshAllowedCidr") or "203.0.113.10/32"
ssh_public_key = config.require("sshPublicKey")

tags = {
    "Project": project_name,
    "Environment": environment,
    "Course": "DevOps-Core-Course",
    "Lab": "04",
    "ManagedBy": "Pulumi",
}

ubuntu = aws.ec2.get_ami(
    most_recent=True,
    owners=["099720109477"],  # Canonical
    filters=[
        aws.ec2.GetAmiFilterArgs(
            name="name",
            values=["ubuntu/images/hvm-ssd-gp3/ubuntu-jammy-22.04-amd64-server-*"],
        ),
        aws.ec2.GetAmiFilterArgs(
            name="virtualization-type",
            values=["hvm"],
        ),
    ],
)

vpc = aws.ec2.Vpc(
    "lab04-vpc",
    cidr_block=vpc_cidr,
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={**tags, "Name": f"{project_name}-vpc"},
)

internet_gateway = aws.ec2.InternetGateway(
    "lab04-igw",
    vpc_id=vpc.id,
    tags={**tags, "Name": f"{project_name}-igw"},
)

subnet = aws.ec2.Subnet(
    "lab04-public-subnet",
    vpc_id=vpc.id,
    cidr_block=public_subnet_cidr,
    availability_zone=availability_zone,
    map_public_ip_on_launch=True,
    tags={**tags, "Name": f"{project_name}-public-subnet"},
)

route_table = aws.ec2.RouteTable(
    "lab04-public-rt",
    vpc_id=vpc.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=internet_gateway.id,
        )
    ],
    tags={**tags, "Name": f"{project_name}-public-rt"},
)

aws.ec2.RouteTableAssociation(
    "lab04-public-rt-association",
    subnet_id=subnet.id,
    route_table_id=route_table.id,
)

security_group = aws.ec2.SecurityGroup(
    "lab04-vm-sg",
    description="Allow SSH, HTTP and app port 5000",
    vpc_id=vpc.id,
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            description="SSH from student IP",
            from_port=22,
            to_port=22,
            protocol="tcp",
            cidr_blocks=[ssh_allowed_cidr],
        ),
        aws.ec2.SecurityGroupIngressArgs(
            description="HTTP",
            from_port=80,
            to_port=80,
            protocol="tcp",
            cidr_blocks=["0.0.0.0/0"],
        ),
        aws.ec2.SecurityGroupIngressArgs(
            description="App 5000",
            from_port=5000,
            to_port=5000,
            protocol="tcp",
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            description="Allow all outbound traffic",
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"],
        )
    ],
    tags={**tags, "Name": f"{project_name}-sg"},
)

key_pair = aws.ec2.KeyPair(
    "lab04-key-pair",
    key_name=f"{project_name}-key",
    public_key=ssh_public_key,
    tags={**tags, "Name": f"{project_name}-key"},
)

instance = aws.ec2.Instance(
    "lab04-vm",
    ami=ubuntu.id,
    instance_type=instance_type,
    subnet_id=subnet.id,
    vpc_security_group_ids=[security_group.id],
    key_name=key_pair.key_name,
    associate_public_ip_address=True,
    root_block_devices=[
        aws.ec2.InstanceRootBlockDeviceArgs(
            volume_size=8,
            volume_type="gp3",
            delete_on_termination=True,
        )
    ],
    tags={**tags, "Name": f"{project_name}-vm"},
)

eip = aws.ec2.Eip(
    "lab04-eip",
    domain="vpc",
    tags={**tags, "Name": f"{project_name}-eip"},
)

aws.ec2.EipAssociation(
    "lab04-eip-association",
    allocation_id=eip.id,
    instance_id=instance.id,
)

pulumi.export("publicIp", eip.public_ip)
pulumi.export("instanceId", instance.id)
pulumi.export(
    "sshCommand",
    pulumi.Output.concat("ssh -i ", ssh_private_key_path, " ", instance_user, "@", eip.public_ip),
)
