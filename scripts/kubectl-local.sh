#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="${OFICINA_HOME:-$HOME/.local/share/oficina-fase4}"
case "$RUNTIME_DIR" in
  /*) ;;
  *) printf 'OFICINA_HOME deve ser um caminho absoluto.\n' >&2; exit 2 ;;
esac
KUBECONFIG_LOCAL="$RUNTIME_DIR/kubeconfig"
if [ ! -s "$KUBECONFIG_LOCAL" ]; then
  printf 'Kubeconfig da Fase 4 nao encontrado. Provisione o cluster pelo repositorio infra-local primeiro.\n' >&2
  exit 1
fi
for argumento in "$@"; do
  case "$argumento" in
    --context|--context=*|--kubeconfig|--kubeconfig=*)
      printf 'Este script so opera o cluster oficina-fase4; nao passe outro contexto ou kubeconfig.\n' >&2
      exit 2
      ;;
  esac
done
exec kubectl --kubeconfig="$KUBECONFIG_LOCAL" --context=kind-oficina-fase4 "$@"
