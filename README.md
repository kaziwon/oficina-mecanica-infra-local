# Infraestrutura local - Fase 4

Base compartilhada da oficina, separada dos tres microsservicos.
Nao precisa clonar Ordens, Execucao ou Cobranca para criar o cluster ou o Sonar.
Os repositorios e recursos das fases anteriores permanecem intactos.

| Repositorio | Responsabilidade |
| --- | --- |
| oficina-mecanica-infra-local | Cluster kind, ElasticMQ persistente e servidor Sonar compartilhados |
| oficina-mecanica-ordens | API, banco, migrations, testes e entrega de Ordens |
| oficina-mecanica-execucao | API, MongoDB, testes e entrega de Execucao |
| oficina-mecanica-cobranca | API, banco, migrations, testes e entrega de Cobranca |

Compartilhar cluster nao significa compartilhar banco ou exigir deploy conjunto.
O CD de um servico nao deve criar/destruir o cluster nem os recursos dos demais.
ElasticMQ oferece filas compativeis com SQS, sem AWS. Gateway e agentes de
monitoramento ficam para uma etapa posterior. New Relic continua externo.

## Cluster

Requisitos: Docker Desktop aberto, Terraform >= 1.7 e kubectl compativel com
Kubernetes 1.35. Nao precisa ativar Kubernetes no Docker Desktop nem instalar
o CLI kind: o provider Terraform usa a biblioteca do kind.

Na raiz deste repositorio:

```bash
bash scripts/cluster.sh init
bash scripts/cluster.sh plan
bash scripts/cluster.sh apply
python3 scripts/deploy_platform.py
bash scripts/kubectl-local.sh get nodes
bash scripts/kubectl-local.sh get pods -A
```

Init instala providers e configura o state. Plan mostra as mudancas; apply cria
a base; deploy_platform.py aplica somente namespace, fila, configuracao e volume
compartilhados e gera as credenciais privadas iniciais. O helper kubectl aponta
explicitamente para oficina-fase4, sem mudar o contexto global.
Veja o [guia do cluster](docs/16-kubernetes-local.md) e o
[passo a passo do deploy](docs/17-deploy-kubernetes-local.md).

O state e o kubeconfig ficam em `~/.local/share/oficina-fase4`, fora dos
repositorios e dos checkouts dos runners. Contem credenciais: nao publicar nem
anexar como artefato. Todos os runners deste ambiente devem usar o mesmo usuario
do computador. `OFICINA_HOME` permite escolher outro diretorio absoluto, mas deve
ser identico em todos os comandos/runners. Mudar essa pasta sem migrar o state
nao transfere o cluster. Use os scripts para nao iniciar um state acidental.

Para destruir intencionalmente o cluster (nao executado automaticamente):

```bash
bash scripts/cluster.sh destroy
```

Destroy remove o cluster inteiro e pode apagar os dados dos bancos e filas.
Nao delete o container do node manualmente. Backup de state nao e backup de banco.

## SonarQube

```bash
docker compose --env-file sonar.env.example -f compose.sonar.yml up -d --wait --wait-timeout 420
```

Abra http://localhost:9000. No primeiro acesso, admin/admin e alteracao de senha.
O projeto Compose tem nome fixo para preservar os volumes quando a pasta muda.
Para parar mantendo os dados, use o mesmo comando trocando `up ...` por `down`,
sem `-v`. Valores do env sao ficticios de laboratorio; uma senha alterada no env
nao altera automaticamente um PostgreSQL ja inicializado.

Projetos, tokens e runners por servico: [guia Sonar](docs/15-sonarqube-local.md).
A analise continua no repositorio de cada servico, nao neste repositorio.

## Verificacao Sem Criar Cluster

```bash
terraform -chdir=cluster init -backend=false
terraform -chdir=cluster fmt -check -recursive
terraform -chdir=cluster validate
terraform -chdir=cluster test
python3 -m venv .venv
.venv/bin/pip install -r tests/requirements.txt
.venv/bin/python -m unittest discover -s tests -v
terraform -chdir=platform init -backend=false -lockfile=readonly
terraform -chdir=platform fmt -check -recursive
terraform -chdir=platform validate
bash -n scripts/cluster.sh scripts/kubectl-local.sh
```

Os testes Terraform usam providers simulados: nao criam recursos Docker.
O CI valida a configuracao; nao provisiona infraestrutura em push/PR.

Ao adicionar ou atualizar providers, gere os checksums para o notebook macOS
ARM64 e para o runner Linux AMD64 antes de commitar o lockfile:

```bash
terraform -chdir=cluster providers lock -platform=darwin_arm64 -platform=linux_amd64
```

O CI usa `-lockfile=readonly`: valida o arquivo versionado sem alterar hashes
durante a execucao. Nao remova essa verificacao para contornar erro de checksum.

## Estado Atual

Cluster e mensageria persistente implementados. Os tres repositorios de servico
possuem bancos proprios, APIs e CD independente no kind. As primeiras analises
reais no Sonar passaram nos tres projetos. O novo CD precisa ser publicado por
PR e validado no GitHub; sua validacao local nao substitui essa execucao.
Metrics-server/HPA e observabilidade distribuida no New Relic continuam pendentes.
