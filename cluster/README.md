# Base Kubernetes local da Fase 4

Este modulo cria APENAS o cluster kind oficina-fase4, com um node e kubeconfig
isolado. Aplicacoes, bancos, mensageria e observabilidade serao provisionados
nas etapas seguintes. Nao cria AWS nem altera a infraestrutura das fases 2/3.

Da raiz de oficina-mecanica-infra-local, com Docker aberto e Terraform >= 1.7:

```bash
bash scripts/cluster.sh init
bash scripts/cluster.sh plan
bash scripts/cluster.sh apply
bash scripts/kubectl-local.sh get nodes
```

O provider Terraform embute a biblioteca do kind; o executavel kind nao e
necessario para este modulo. State e kubeconfig ficam em ~/.local/share/oficina-fase4,
fora dos checkouts. Contem credenciais: preserve-os e nao os publique como artefatos.
Use os scripts para configurar o backend local persistente corretamente.

```bash
bash scripts/cluster.sh test
bash scripts/cluster.sh destroy
```

Os testes usam provider simulado e nao criam clusters. Destroy remove este
cluster e, futuramente, perdera os dados armazenados DENTRO dele. Nao execute
para apenas pausar os estudos depois que os bancos forem instalados. Nunca
apague manualmente o container para substituir o gerenciamento pelo Terraform.

local_sensitive_file.kubeconfig exporta as credenciais para fora do checkout.
O provider kind trata mudar kubeconfig_path como substituicao do cluster; por
isso apenas esse atributo local e ignorado depois da criacao. Imagem, portas
e topologia continuam comparadas normalmente. Isso permite mover o state
da base inicial sem recriar o node.

Detalhes e proximas etapas: [guia central](../docs/16-kubernetes-local.md).
