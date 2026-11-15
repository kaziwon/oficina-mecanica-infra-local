resource "kubernetes_namespace_v1" "new_relic" {
  metadata {
    name   = "newrelic"
    labels = { "app.kubernetes.io/part-of" = "oficina-fase4" }
  }
}

resource "kubernetes_secret_v1" "license" {
  count = var.enabled ? 1 : 0
  metadata {
    name      = "newrelic-license"
    namespace = kubernetes_namespace_v1.new_relic.metadata[0].name
  }
  data = { license = var.license_key }
}

resource "helm_release" "new_relic" {
  count           = var.enabled ? 1 : 0
  name            = "newrelic"
  namespace       = kubernetes_namespace_v1.new_relic.metadata[0].name
  repository      = "https://helm-charts.newrelic.com"
  chart           = "nri-bundle"
  version         = "8.0.40"
  atomic          = true
  cleanup_on_fail = true
  wait            = true
  timeout         = 600
  max_history     = 3
  values          = [file("${path.module}/values.yaml")]
  depends_on      = [kubernetes_secret_v1.license]
}

output "cluster_name" {
  value = "oficina-fase4"
}

output "monitoring_enabled" {
  value = var.enabled
}
