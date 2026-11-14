# Entrega local com kind

## Decisao da Fase 4

A entrega da Fase 4 passa a usar Kubernetes local com kind. AWS/EKS/RDS/ECR/SQS
nao serao o destino desse ambiente. Os repositorios e a entrega da Fase 3
permanecem intactos. New Relic continua externo, recebendo a telemetria local.
Nao se trata de substituir Kubernetes por Docker Compose: o deploy final sera
feito no cluster local, pelos workflows dos tres servicos.

Arquitetura planejada:

```text
GitHub: PR -> build/testes/cobertura em runner hospedado
GitHub: main -> Sonar em runner local -> CD em runner local
                                        |
                                  kind oficina-fase4
                                  /       |        \
                               Ordens  Execucao  Cobranca
                               MySQL   MongoDB    MySQL
                                    mensageria

SonarQube + PostgreSQL: Docker local, fora do cluster da oficina
New Relic: externo, recebendo logs, metricas e traces
```

Cada servico continua com seu repositorio, banco, configuracao de aplicacao e
pipeline independente. O cluster e infraestrutura compartilhada e sua base
fica em oficina-mecanica-infra-local, em cluster/. Os recursos de aplicacao de cada servico
ficarao no seu proprio repositorio; CD de um servico nao deve destruir os outros.

## Implementado nesta primeira etapa

- Modulo Terraform para criar kind oficina-fase4, separado dos clusters antigos.
- Um unico node control-plane, adequado ao laboratorio inicial no notebook.
- Provider e imagem de node fixados. Kubernetes 1.35 e compativel com o kubectl
  1.34 ja instalado (uma versao minor de diferenca).
- API do cluster e portas reservadas vinculadas apenas a 127.0.0.1.
- Kubeconfig proprio, sem mudar o contexto padrao do usuario.
- Testes simulados de configuracao e helper de kubectl para evitar cluster errado.

Ainda NAO provisiona as APIs, bancos, filas, metrics-server, gateway, HPA ou os
agentes New Relic. As portas abaixo estao somente reservadas, sem endpoints ativos:

| Uso futuro | Porta no computador | NodePort reservado |
| --- | ---: | ---: |
| Gateway | 18090 | 30080 |
| Ordens | 18101 | 30101 |
| Execucao | 18102 | 30102 |
| Cobranca | 18103 | 30103 |

Isso nao altera os ports 18091-18094 do Compose integrado de desenvolvimento,
nem o Sonar em 9000. Evite manter dois ambientes completos ligados sem necessidade:
o Docker deste notebook esta configurado com aproximadamente 8 GB de memoria.

## Criar e consultar a base

Na raiz de oficina-mecanica-infra-local, com Docker Desktop aberto:

```bash
bash scripts/cluster.sh init
bash scripts/cluster.sh plan
bash scripts/cluster.sh apply
```

Init instala os providers fixados e aponta para o state persistente. Plan mostra
kind_cluster.fase4 e o arquivo local de acesso. Apply cria o node Docker e espera
Kubernetes ficar pronto; nao recria o cluster quando o state ja o conhece.
Nao e necessario ativar o Kubernetes do Docker Desktop: kind cria seu cluster
independente usando o Docker. Tambem nao precisa instalar o CLI kind nesta etapa,
pois o provider usa a biblioteca do kind diretamente.

Para consultar SEM export KUBECONFIG e sem mudar ~/.kube/config:

```bash
bash scripts/kubectl-local.sh get nodes
bash scripts/kubectl-local.sh get pods -A
```

O helper sempre usa o arquivo e contexto da Fase 4. Se faltar kubeconfig, falha
com orientacao em vez de tentar localhost:8080 ou outro cluster. Nao aceita
sobrescrever contexto/kubeconfig nos argumentos. Tambem e possivel consultar
o caminho usando bash scripts/cluster.sh output -raw kubeconfig_path.

## State e ciclo de vida

State e kubeconfig ficam em ~/.local/share/oficina-fase4, fora dos repositorios
e checkouts de runners. OFICINA_HOME permite outro caminho absoluto; todos os
runners devem usar a mesma pasta e usuario do computador. Trocar a pasta exige
migrar o state existente, nao e uma forma de mover automaticamente o cluster.
O state tem chaves e certificados do cluster: nao deve entrar em commit, log ou
artefato publico. O arquivo .terraform.lock.hcl deve ser versionado.

Como antes, nao apague o container do node manualmente e nao jogue o state fora
para resolver erros. Para remover intencionalmente este ambiente:

```bash
bash scripts/cluster.sh destroy
```

Depois que houver bancos no cluster, destroy tambem pode apagar seus dados.
Mudar imagem, portas ou topologia exige recriar o cluster neste provider; por
isso a base tem state separado dos futuros deploys das aplicacoes.
Backup e persistencia dos bancos precisam estar definidos antes dessa etapa.

## Runners e proximos incrementos

Continua sendo um runner por repositorio, em pastas proprias fora do codigo.
Cadastre os labels sonar-local e kind-local: o primeiro sera usado na qualidade;
o segundo, no futuro CD. O runner da Fase 3 nao deve ser reutilizado/reconfigurado.
O runner precisa enxergar o mesmo Docker e kubeconfig local do cluster.
Nao dispare deploy a partir de forks ou codigo nao revisado de PRs.

Proximos passos, sem considerar esta base um deploy completo:

1. Provisionar bancos e mensageria locais com persistencia e credenciais isoladas.
2. Adicionar os recursos Kubernetes de cada servico no respectivo repositorio.
3. Automatizar build, carregamento de imagem no kind, migrations e rollout por servico.
4. Integrar quality gate ao CD, preservando testes/PRs e Sonar local.
5. Instalar/validar observabilidade New Relic, metricas e escalabilidade no cluster.
6. Reexecutar o fluxo completo e as falhas da Saga; consolidar documentacao/video.

Fontes oficiais:

- https://kind.sigs.k8s.io/docs/user/configuration/
- https://registry.terraform.io/providers/tehcyx/kind/0.13.0/docs/resources/cluster
