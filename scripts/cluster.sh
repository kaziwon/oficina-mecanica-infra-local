#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${OFICINA_HOME:-$HOME/.local/share/oficina-fase4}"
case "$RUNTIME_DIR" in
  /*) ;;
  *) printf 'OFICINA_HOME deve ser um caminho absoluto.\n' >&2; exit 2 ;;
esac

comando="${1:-}"
case "$comando" in
  init|validate|fmt|test|plan|apply|destroy|output) ;;
  *) printf 'Uso: bash scripts/cluster.sh {init|validate|fmt|test|plan|apply|destroy|output} [argumentos]\n' >&2; exit 2 ;;
esac
shift

mkdir -p "$RUNTIME_DIR/terraform"
chmod 700 "$RUNTIME_DIR" "$RUNTIME_DIR/terraform"
export TF_VAR_runtime_dir="$RUNTIME_DIR"
# Cada checkout tem cache proprio; todos usam o mesmo state local persistente.
export TF_DATA_DIR="$ROOT_DIR/cluster/.terraform"
if [ "$comando" = init ]; then
  exec terraform -chdir="$ROOT_DIR/cluster" init \
    -backend-config="path=$RUNTIME_DIR/terraform/cluster.tfstate" "$@"
fi
exec terraform -chdir="$ROOT_DIR/cluster" "$comando" "$@"
