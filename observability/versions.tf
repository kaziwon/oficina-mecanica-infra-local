terraform {
  required_version = ">= 1.9.0, < 2.0.0"
  backend "local" {}
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "3.5.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "3.3.0"
    }
  }
}

variable "runtime_dir" {
  type    = string
  default = "~/.local/share/oficina-fase4"
}

variable "enabled" {
  type    = bool
  default = false
}

variable "license_key" {
  type      = string
  sensitive = true
  default   = ""
  validation {
    condition     = !var.enabled || can(regex("^[A-Za-z0-9_-]{20,256}$", var.license_key))
    error_message = "Configure uma license key valida para habilitar os agentes."
  }
}

provider "kubernetes" {
  config_path    = "${pathexpand(var.runtime_dir)}/kubeconfig"
  config_context = "kind-oficina-fase4"
}

provider "helm" {
  kubernetes = {
    config_path    = "${pathexpand(var.runtime_dir)}/kubeconfig"
    config_context = "kind-oficina-fase4"
  }
}
