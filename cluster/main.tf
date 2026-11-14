locals {
  kubeconfig_path = "${abspath(pathexpand(var.runtime_dir))}/kubeconfig"
  cluster_name    = "oficina-fase4"
  node_image      = "kindest/node:v1.35.8@sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0"

  port_mappings = {
    gateway  = { container_port = 30080, host_port = 18090 }
    ordens   = { container_port = 30101, host_port = 18101 }
    execucao = { container_port = 30102, host_port = 18102 }
    cobranca = { container_port = 30103, host_port = 18103 }
  }
}

provider "kind" {}

resource "kind_cluster" "fase4" {
  name            = local.cluster_name
  node_image      = local.node_image
  wait_for_ready  = true
  kubeconfig_path = local.kubeconfig_path

  lifecycle {
    # Mover o arquivo local nao deve recriar um cluster ja existente.
    # O arquivo atual e gerenciado separadamente abaixo.
    ignore_changes = [kubeconfig_path]
  }

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    networking {
      api_server_address = "127.0.0.1"
    }

    node {
      role = "control-plane"

      dynamic "extra_port_mappings" {
        for_each = local.port_mappings
        content {
          container_port = extra_port_mappings.value.container_port
          host_port      = extra_port_mappings.value.host_port
          listen_address = "127.0.0.1"
          protocol       = "TCP"
        }
      }
    }
  }
}

resource "local_sensitive_file" "kubeconfig" {
  content              = sensitive(kind_cluster.fase4.kubeconfig)
  filename             = local.kubeconfig_path
  file_permission      = "0600"
  directory_permission = "0700"
}
