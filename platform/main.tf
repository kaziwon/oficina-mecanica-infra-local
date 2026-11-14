locals {
  namespace = "oficina-plataforma"
}

resource "kubernetes_namespace_v1" "platform" {
  metadata {
    name   = local.namespace
    labels = { "app.kubernetes.io/part-of" = "oficina-fase4" }
  }
  lifecycle { prevent_destroy = true }
}

resource "kubernetes_persistent_volume_claim_v1" "messages" {
  metadata {
    name      = "elasticmq-data"
    namespace = kubernetes_namespace_v1.platform.metadata[0].name
  }
  spec {
    access_modes = ["ReadWriteOnce"]
    resources { requests = { storage = "1Gi" } }
    storage_class_name = "standard"
  }
  wait_until_bound = false
  lifecycle { prevent_destroy = true }
}

resource "kubernetes_config_map_v1" "messages" {
  metadata {
    name      = "elasticmq-config"
    namespace = kubernetes_namespace_v1.platform.metadata[0].name
  }
  data = { "elasticmq.conf" = file("${path.module}/../k8s/elasticmq.conf") }
}

resource "kubernetes_manifest" "messages_service" {
  manifest   = yamldecode(file("${path.module}/../k8s/elasticmq-service.yaml"))
  depends_on = [kubernetes_namespace_v1.platform]
}

resource "kubernetes_manifest" "messages" {
  manifest = yamldecode(templatefile("${path.module}/../k8s/elasticmq-statefulset.yaml.tftpl", {
    config_checksum = sha256(kubernetes_config_map_v1.messages.data["elasticmq.conf"])
  }))
  depends_on = [kubernetes_persistent_volume_claim_v1.messages, kubernetes_manifest.messages_service]
  wait { rollout = true }
  timeouts {
    create = "8m"
    update = "8m"
  }
}

output "messaging_endpoint" {
  value = "http://elasticmq.oficina-plataforma.svc.cluster.local:9324"
}
