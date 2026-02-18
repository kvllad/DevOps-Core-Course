output "repository_full_name" {
  description = "Managed repository full name"
  value       = github_repository.course_repo.full_name
}

output "repository_html_url" {
  description = "Managed repository URL"
  value       = github_repository.course_repo.html_url
}
