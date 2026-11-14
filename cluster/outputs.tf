output "cluster_name" {
  description = "Cluster compartilhado exclusivo da Fase 4."
  value       = kind_cluster.fase4.name
}

output "context" {
  description = "Contexto explicito a usar com o kubeconfig deste cluster."
  value       = "kind-${local.cluster_name}"
}

output "kubeconfig_path" {
  description = "Arquivo local para consultar o cluster; nao altera ~/.kube/config."
  value       = local_sensitive_file.kubeconfig.filename
}

output "reserved_ports" {
  description = "Portas reservadas para futuros Services; ainda nao ha aplicacoes publicadas."
  value       = { for name, mapping in local.port_mappings : name => mapping.host_port }
}
