mock_provider "kind" {}
mock_provider "local" {}

variables {
  runtime_dir = "/tmp/oficina-fase4-teste"
}

run "cluster_local_isolado" {
  command = plan

  assert {
    condition     = kind_cluster.fase4.name == "oficina-fase4"
    error_message = "O cluster deve ter identidade exclusiva da Fase 4."
  }

  assert {
    condition     = length(kind_cluster.fase4.kind_config[0].node) == 1
    error_message = "A base local deve criar somente um node."
  }

  assert {
    condition     = kind_cluster.fase4.kind_config[0].networking[0].api_server_address == "127.0.0.1"
    error_message = "O Kubernetes nao deve publicar a API fora do computador local."
  }

  assert {
    condition = alltrue([
      for mapping in kind_cluster.fase4.kind_config[0].node[0].extra_port_mappings :
      mapping.listen_address == "127.0.0.1"
    ])
    error_message = "As portas reservadas devem estar restritas a loopback."
  }

  assert {
    condition     = local_sensitive_file.kubeconfig.filename == "/tmp/oficina-fase4-teste/kubeconfig"
    error_message = "O kubeconfig nao deve sobrescrever o arquivo global do usuario."
  }

  assert {
    condition     = local_sensitive_file.kubeconfig.file_permission == "0600"
    error_message = "O kubeconfig deve ser legivel somente pelo dono."
  }
}
