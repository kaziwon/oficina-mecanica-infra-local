# Deploy independente no kind

## O que cada repositorio administra

| Repositorio | Namespace | Recursos proprios |
| --- | --- | --- |
| infra-local | oficina-plataforma | ElasticMQ, filas/DLQs, ConfigMap, Service e PVC |
| ordens | oficina-ordens | API, MySQL, migrations, configuracoes e PVC |
| execucao | oficina-execucao | API, Mongo autenticado replica set, bootstrap e PVC |
| cobranca | oficina-cobranca | API, MySQL, migrations e mock OAuth/pagamento com PVC |

O cluster e o Sonar tambem pertencem a infra-local. Compartilhar cluster/fila
nao compartilha bancos: nenhum servico usa credenciais do banco de outro.
Os helpers Python sao copias locais pequenas, nao imports de outro repositorio.
Cada entrega usa o Dockerfile, manifestos e state do proprio servico.

## Preparar a base uma vez

Docker Desktop aberto, Python 3.10+, Terraform 1.15.7 e kubectl compativel com
Kubernetes 1.35 disponiveis no PATH. Nao precisa ativar Kubernetes no Docker
Desktop. Todos os runners usam o mesmo usuario local e o mesmo OFICINA_HOME.

Na raiz de oficina-mecanica-infra-local:

```bash
bash scripts/cluster.sh init
bash scripts/cluster.sh plan
bash scripts/cluster.sh apply
python3 scripts/deploy_platform.py
bash scripts/kubectl-local.sh get pods -A
```

Os tres primeiros comandos criam/conferem o cluster. O quarto cria a mensageria
persistente e credenciais privadas iniciais. Nao inicia APIs nem aplica os
modulos dos outros repositorios. Para somente conferir a plataforma:

```bash
python3 scripts/deploy_platform.py --plan-only
```

## Publicar cada servico manualmente

Na raiz de CADA repositorio de servico, separadamente:

```bash
python3 scripts/deploy_local.py
```

Esse comando e o caminho manual de desenvolvimento: nao consulta checks do
GitHub e pode testar codigo ainda nao commitado. Nao representa aprovacao do CI.
Na primeira execucao, cria uma senha propria para o banco e gera a configuracao
privada. Faz build da imagem, carrega no node do kind, planeja e aplica somente
os recursos do servico. Nao precisa clonar nem implantar os outros servicos para
publicar um deles; fluxos de negocio distribuidos precisam dos tres em execucao.

No macOS ARM64, o helper baixa o CLI kind v0.33.0 oficial e verifica SHA256;
o binario fica no diretorio privado do ambiente, nao no PATH global. Em outra
plataforma, instale a mesma versao em $OFICINA_HOME/bin/kind.

O Kubernetes YAML em k8s/ e a fonte dos manifestos; o Terraform em
infra/kubernetes/ renderiza as variaveis e administra esses mesmos recursos.
Nao rode kubectl apply sobre os templates: isso contornaria o state.

| Servico | Swagger | Readiness |
| --- | --- | --- |
| Ordens | http://127.0.0.1:18101/swagger/index.html | http://127.0.0.1:18101/health/ready |
| Execucao | http://127.0.0.1:18102/swagger/index.html | http://127.0.0.1:18102/health/ready |
| Cobranca | http://127.0.0.1:18103/swagger/index.html | http://127.0.0.1:18103/health/ready |

NodePort + mapeamento do kind publicam somente em loopback, sem port-forward.
Bancos, fila e mock usam apenas Services internos, sem portas no computador.
O ambiente e academico local, sem TLS/alta disponibilidade; nao e uma arquitetura
de producao pronta para internet. O mock nao movimenta dinheiro real.

## Ordem das migrations e das sondas

Ordens/Cobranca: MySQL saudavel -> Job de migrations -> API. O Job usa a mesma
imagem da API com Database__ApplyMigrations=true e Database__MigrateOnly=true;
aplica migrations e encerra sem HTTP/workers. A API normal usa ApplyMigrations=false,
evitando concorrencia entre replicas. Uma falha no Job impede a atualizacao da API.
Nao ha rollback automatico de schema; migrations precisam ser retrocompativeis.

Execucao: Mongo autenticado -> Job que inicia/confere rs0 -> API e indices.
A replica set permite as transacoes locais do servico. Reiniciar nao reinicializa
o banco nem recria senhas. Cobranca tambem espera o mock ficar pronto.

Startup/readiness consultam /health/ready (banco). Liveness usa /health, sem
reiniciar a API apenas porque o banco ficou indisponivel. Resources definem
requests/limits; o acesso HTTP segue os JWTs existentes da aplicacao.

## CD no GitHub

Depois de publicar estes arquivos por PR e merge:

1. PR e push na main executam Integracao continua: build, testes, cobertura e validacao Kubernetes.
2. CI aprovado na main dispara Qualidade local, analisando o mesmo SHA no Sonar.
3. Sonar aprovado dispara Entrega continua local no runner kind-local daquele repositorio.
4. O deploy reconfirma CI e Sonar aprovados para o SHA exato e verifica que ele ainda e a main atual.
5. Constroi imagem com tag SHA, carrega no kind, aplica migrations e espera o rollout.

Se um check falhar, o novo deploy nao comeca. Um resultado verde antigo nao
autoriza outro commit. Execucoes de PR/fork nao rodam no computador pessoal.
Proteja main e revise todo codigo que sera executado pelos runners.

Tambem e possivel Actions > Entrega continua local > Run workflow > main.
O disparo manual mantem todas as verificacoes de SHA/CI/Sonar; nao e um bypass.
Se uma revisao foi superada por outra main, o workflow antigo falha sem implanta-la.
Se a main avancar antes de criar o job Sonar de um CI antigo, esse job e pulado:
workflow_run usa o SHA da branch padrao em sua propria execucao. A condicao
confere que ele coincide com o SHA analisado, evitando atribuir resultado a outro
commit. O CI da revisao atual inicia sua propria cadeia normalmente.
O summary mostra o endereco local. Nao precisa de credencial AWS nem de um
quarto runner para a base, preparada localmente uma vez.

Os tres runners precisam estar ativos com labels sonar-local e kind-local.
Um mutex de arquivo serializa qualidade/deploy no mesmo notebook para conter
o uso de RAM, sem juntar os releases dos servicos. Nao delete o lock enquanto
houver uma operacao em execucao. O Sonar local deve estar acessivel em 9000.

## Consultar e preservar os dados

Na raiz de infra-local:

```bash
bash scripts/kubectl-local.sh get pods,pvc -n oficina-ordens
bash scripts/kubectl-local.sh get pods,pvc -n oficina-execucao
bash scripts/kubectl-local.sh get pods,pvc -n oficina-cobranca
bash scripts/kubectl-local.sh get pods,pvc -n oficina-plataforma
bash scripts/kubectl-local.sh logs -n oficina-ordens deployment/api --tail=40
```

Login administrativo: POST /api/auth/login, body com username admin e password
da chave admin_password em ~/.local/share/oficina-fase4/secrets/common.json.
Abra esse arquivo apenas localmente; nao publique a senha nem coloque em print.
O login de cliente por CPF continua separado. Nunca imprima os Secrets nos logs
do GitHub. Para a base atual, os tokens SONAR_TOKEN ja cadastrados continuam iguais.

| Diretorio privado | Conteudo |
| --- | --- |
| terraform/ | states separados de cluster, platform e cada servico |
| secrets/ | credenciais comuns e credenciais exclusivas de cada banco/mock |
| config/ | tfvars JSON gerados, incluindo valores sensiveis |
| kubeconfig | acesso explicito somente ao cluster oficina-fase4 |

Tudo fica sob ~/.local/share/oficina-fase4 (ou OFICINA_HOME absoluto), fora do
checkout do runner. Arquivos privados usam permissao 600, pastas 700. States e
planos tambem podem conter senhas; nao anexar em artefatos/commits. Nao apague
essa pasta para corrigir erro: perder senhas com PVC existente faz o helper
interromper a operacao, em vez de sobrescrever o banco. Backup deve proteger
esse diretorio E os dados dos volumes. PVC nao e backup.

ElasticMQ usa H2 em volume para mensagens e arquivo persistente para filas.
Existem filas de comandos de Execucao/Cobranca, eventos de Ordens e DLQs com
cinco tentativas. Pods/Deployments podem reiniciar preservando PVCs. Namespaces
e PVCs tem prevent_destroy no Terraform. Isso NAO impede perder dados se
destruir o cluster/container kind ou apagar um volume manualmente.

O Compose integrado antigo usa 18091-18094 e volumes diferentes. Para poupar
memoria, mantenha apenas um ambiente de negocio completo ligado. Na raiz de
Ordens, parar esse Compose sem apagar dados:

```bash
docker compose -f compose.integracao.yml stop
```

Pode voltar com o up documentado no README; nao use down -v se quer preservar
seus dados. Sonar e outro projeto Compose e deve continuar ligado para o CI local.

## Limites desta etapa

Os recursos e o caminho manual sao validados no cluster local. A execucao real
do novo CD no GitHub depende de commit/PR/merge; testes locais nao a substituem.
Ainda faltam New Relic distribuido, metrics-server/HPA, BDD automatico no CI e
evidencias finais. Nenhum deploy AWS ou alteracao nas fases anteriores e necessario.

## Verificacoes desta implementacao

Fotografia local em 2026-11-14, a ser reexecutada apos alteracoes:

- 539 testes .NET passaram sem ignorados; cobertura de Ordens 93,90%, Execucao 96,32% e Cobranca 92,14%.
- 51 testes dos helpers/manifestos/gates dos servicos e 11 da infraestrutura passaram.
- Os tres cenarios BDD passaram nos endpoints do kind: entrega, recusa e compensacao paga.
- Fila e mensagem ficticias sobreviveram ao reinicio do pod ElasticMQ.
- Dados dos tres bancos sobreviveram ao reinicio dos respectivos pods; as APIs nao reiniciaram por isso.
- Uma nova imagem de Ordens foi implantada sem alterar pods/PVCs de Execucao, Cobranca ou plataforma.
- Workflows validados com actionlint; Terraform validado no macOS e lockfile/provider conferidos em Linux AMD64.

O provider precisa aceitar os campos gerados pelo Kubernetes: labels de Jobs
sao computed_fields, e o Deployment inclui uma anotacao de rollout calculada
da imagem/configuracao/template. Isso acompanha as anotacoes de revisao do
controlador tambem em atualizacoes, sem ignorar as mudancas desejadas no spec.
Referencia: [documentacao do provider](https://registry.terraform.io/providers/hashicorp/kubernetes/3.5.0/docs/resources/manifest).
O encadeamento de revisoes segue os [eventos do GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run).
