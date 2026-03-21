provider "github" {
  owner = var.github_owner
}

resource "github_repository" "course_repo" {
  name        = var.repository_name
  description = var.repository_description
  visibility  = var.repository_visibility

  has_issues   = var.has_issues
  has_wiki     = var.has_wiki
  has_projects = false

  delete_branch_on_merge = true
  vulnerability_alerts   = true
}
