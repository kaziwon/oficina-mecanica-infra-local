terraform {
  required_version = ">= 1.7.0, < 2.0.0"
  backend "local" {}
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "3.5.0"
    }
  }
}

variable "runtime_dir" {
  type    = string
  default = "~/.local/share/oficina-fase4"
}

provider "kubernetes" {
  config_path    = "${pathexpand(var.runtime_dir)}/kubeconfig"
  config_context = "kind-oficina-fase4"
}
