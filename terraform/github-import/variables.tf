variable "github_owner" {
  description = "GitHub username or organization"
  type        = string
}

variable "repository_name" {
  description = "Repository name to import/manage"
  type        = string
  default     = "DevOps-Core-Course"
}

variable "repository_description" {
  description = "Repository description managed by Terraform"
  type        = string
  default     = "DevOps course lab assignments"
}

variable "repository_visibility" {
  description = "Visibility for repository"
  type        = string
  default     = "public"

  validation {
    condition     = contains(["public", "private", "internal"], var.repository_visibility)
    error_message = "repository_visibility must be one of: public, private, internal."
  }
}

variable "has_issues" {
  description = "Enable GitHub issues"
  type        = bool
  default     = true
}

variable "has_wiki" {
  description = "Enable GitHub wiki"
  type        = bool
  default     = false
}
