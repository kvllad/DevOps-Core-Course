output "vm_public_ip" {
  description = "Public IP address for SSH and HTTP access"
  value       = aws_eip.vm.public_ip
}

output "vm_instance_id" {
  description = "EC2 instance identifier"
  value       = aws_instance.vm.id
}

output "vm_ssh_command" {
  description = "Command to connect to VM via SSH"
  value       = "ssh -i ${var.ssh_private_key_path} ${var.instance_user}@${aws_eip.vm.public_ip}"
}
