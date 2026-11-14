terraform {
  required_version = ">= 1.7.0, < 2.0.0"

  backend "local" {}

  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "0.13.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "2.9.1"
    }
  }
}
