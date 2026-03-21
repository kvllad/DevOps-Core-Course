variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "availability_zone" {
  description = "Availability Zone for the public subnet"
  type        = string
  default     = "us-east-1a"
}

variable "project_name" {
  description = "Project name used in resource tags"
  type        = string
  default     = "devops-core-course-lab04"
}

variable "environment" {
  description = "Environment label for tags"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.42.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for public subnet"
  type        = string
  default     = "10.42.1.0/24"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 8
}

variable "ssh_public_key_path" {
  description = "Path to local SSH public key file"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "ssh_private_key_path" {
  description = "Path to local SSH private key file used in output command"
  type        = string
  default     = "~/.ssh/id_ed25519"
}

variable "ssh_allowed_cidr" {
  description = "CIDR allowed to connect via SSH (use your public IP /32)"
  type        = string
  default     = "203.0.113.10/32"
}

variable "instance_user" {
  description = "Default SSH username for Ubuntu image"
  type        = string
  default     = "ubuntu"
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default = {
    Owner    = "student"
    Course   = "DevOps-Core-Course"
    Lab      = "04"
    Managed  = "terraform"
  }
}
