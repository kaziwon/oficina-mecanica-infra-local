# New Relic na Fase 4

## Escopo

O laboratorio continua local, no kind oficina-fase4. A telemetria sai por HTTPS
para a conta New Relic ja usada na Fase 3. Nao cria recursos AWS.

| Entidade no New Relic | Origem |
| --- | --- |
| oficina-fase4-ordens | API e consumidor/publicador de Ordens |
| oficina-fase4-execucao | API e consumidor/publicador de Execucao |
| oficina-fase4-cobranca | API, mensageria e chamadas de pagamento/estorno mock |
| oficina-fase4 | Cluster Kubernetes, nodes, pods e containers |

Os agentes .NET ficam nas imagens Linux, fixados na versao 10.57.0 e verificados
por SHA256 em ARM64 e AMD64. Fora do kind, as imagens continuam com profiling
desabilitado por padrao. dotnet run no macOS nao carrega esse profiler Linux.
Nenhum pacote New Relic foi adicionado a Domain, Application ou InterfaceAdapters.

No cluster, o chart oficial nri-bundle 8.0.40 usa lowDataMode, limites de
CPU/memoria e somente os componentes necessarios: infraestrutura e KSM.
Nao habilita Pixie, eBPF ou um segundo pipeline de logs.
O agente de infraestrutura usa privilegios e acesso ao host do node kind para
coletar metricas; nao deve ser instalado em outro cluster pelo mesmo comando.
O kubelet local usa o modo de compatibilidade de certificados do chart;
o envio ao New Relic continua usando HTTPS.

## Habilitar

Com Docker/cluster prontos, na raiz de infra-local:

```bash
python3 scripts/configure_newrelic.py
python3 scripts/deploy_observability.py --plan-only
python3 scripts/deploy_observability.py
bash scripts/kubectl-local.sh get pods -n newrelic
```

O primeiro comando pede a LICENSE KEY de ingestao sem mostra-la. Nao e uma User
API Key NRAK. Alternativamente, aceita NEW_RELIC_LICENSE_KEY no ambiente para
integracoes locais; nao coloque o valor em historico, commit ou argumento CLI.

A configuracao fica em ~/.local/share/oficina-fase4/secrets/newrelic.json,
permissao 600, fora dos checkouts. OFICINA_HOME deve ser igual para todos os
runners. Terraform usa state observability.tfstate separado da plataforma e
dos servicos; ele tambem contem dados sensiveis e nao e artefato de CI.

Depois, na raiz de cada servico:

```bash
python3 scripts/deploy_local.py
```

O mesmo script usado pelo CD le a configuracao privada, preenche o Secret
Kubernetes e habilita o profiler. Nao precisa cadastrar a license key em tres
Secrets GitHub quando os runners usam este mesmo ambiente local. Ela nunca e
ARG/ENV de build Docker, nao e embutida na imagem nem nos values do Helm.
As migrations desabilitam explicitamente o agente, mesmo usando a imagem da API.

Para outra pessoa clonar e subir o projeto, a configuracao e opcional: sem esse
arquivo, a aplicacao roda normalmente, sem enviar telemetria.

## O que muda na mensageria

O agente rastreia ASP.NET Core, HTTP e o SDK SQS. Como os consumidores sao
BackgroundServices proprios, a configuracao XML cria transacoes finitas em
PublicarMensagem e ReceberEProcessar. Nao instrumenta o loop ExecuteAsync inteiro.
No SDK AWS v4, o envio inicializa MessageAttributes para permitir ao agente
inserir os headers de tracing; isso nao altera o JSON do contrato da Saga.

Os metodos foram extraidos somente na camada HTTP/host. A confirmacao da fila
continua DEPOIS da transacao local. Falhas preservam reentrega/DLQ; os novos testes
verificam esse comportamento com SQS local descartavel.

Em Cobranca, o XML tambem observa os sources HTTP de cobranca, estorno e consulta
financeira, sem mudar suas regras nem adicionar biblioteca de monitoramento ao core.
Esses traces mostram as chamadas OAuth e ao provedor mock.

## Correlacao nao e uma unica transacao de horas

Uma OS tem etapas assincronas e pode aguardar uma pessoa aprovar o orcamento.
O contexto de um request HTTP nao e persistido pela outbox. Portanto, nao
prometemos um unico trace.id do cadastro ate a entrega do veiculo.

- O trace conecta a publicacao e o consumo SQS instrumentados, e chamadas HTTP relacionadas.
- MessageId une publicacao/consumo daquela mensagem.
- SagaId e CorrelationId acompanham o processo inteiro nos logs, inclusive entre traces diferentes.
- Os IDs sao preservados em reentregas; nao sao substituidos por IDs novos de monitoramento.

ReceberEProcessar tambem faz polling quando a fila esta vazia. Seu contador de
transacoes NAO equivale ao volume de OS. Use os logs de mensagens ou indicadores
de negocio especificos; nao conte polls como ordens criadas.

## Conferir no site

Gere uma OS pelo fluxo normal ou execute os BDDs no kind (guia 14 de Ordens).
Espere alguns minutos pela primeira coleta. Em APM & services, procure as tres
entidades da tabela. Em Kubernetes, selecione oficina-fase4.

No Query builder, latencia das APIs:

```sql
FROM Transaction
SELECT count(*) AS 'Requisicoes',
       average(duration) * 1000 AS 'Latencia media (ms)',
       percentile(duration, 95) * 1000 AS 'p95 (ms)'
WHERE appName IN ('oficina-fase4-ordens', 'oficina-fase4-execucao', 'oficina-fase4-cobranca')
  AND type = 'Web'
FACET appName
SINCE 30 minutes ago
```

Logs de uma Saga completa, substituindo o GUID ficticio pelo sagaId real:

```sql
FROM Log
SELECT timestamp, `entity.name`, message, `trace.id`, `span.id`
WHERE `entity.name` IN ('oficina-fase4-ordens', 'oficina-fase4-execucao', 'oficina-fase4-cobranca')
  AND message LIKE '%GUID_DA_SAGA%'
SINCE 30 minutes ago
LIMIT 200
```

A busca por message funciona mesmo se a versao do agente apresentar os campos
de contexto com prefixo. Em Logs, filtre pelo mesmo GUID, abra uma entrada e
use trace.id para navegar ao trace. O publicador e o consumidor da mesma
mensagem devem aparecer no rastreamento, conforme a amostragem do agente.
Alguns traces podem nao ser amostrados; isso nao muda os IDs nem a Saga.

Erros de API e de processos instrumentados:

```sql
FROM TransactionError
SELECT count(*)
WHERE appName IN ('oficina-fase4-ordens', 'oficina-fase4-execucao', 'oficina-fase4-cobranca')
FACET appName, transactionName
SINCE 30 minutes ago
```

Para conferir os atributos de containers disponiveis na versao instalada:

```sql
FROM K8sContainerSample
SELECT keyset()
WHERE clusterName = 'oficina-fase4'
SINCE 30 minutes ago
```

A tela Kubernetes fornece CPU, memoria, estados e reinicios sem criar dashboard
customizado. Use as abas de pods/containers dos namespaces oficina-ordens,
oficina-execucao e oficina-cobranca para o video.

## Seguranca e limites

Os logs existentes sao enviados pelo agente .NET uma unica vez; nao instalamos
Fluent Bit em paralelo. O profiler nativo escreve em /tmp/newrelic; o diagnostico
do agente gerenciado usa console em nivel info, compativel com a API non-root
e filesystem read-only. As mensagens da aplicacao continuam em JSON. Corpos HTTP, headers e
parametros de request nao devem ser usados como atributos de negocio; a coleta
de SQL textual foi desabilitada. Nao envie CPFs, senhas, tokens ou payloads de
pagamento nos logs. Os collectors KSM nao incluem Secrets nem ConfigMaps.

Readiness/liveness continuam no Kubernetes. Nao foi criado Synthetic publico
para 127.0.0.1: o New Relic na internet nao alcanca esse endereco local.
Uptime externo precisa de uma localizacao privada ou endpoint realmente
acessivel. Alertas/painel de negocio personalizados nao sao provisionados aqui;
esta etapa integra APM, logs, traces e metricas Kubernetes da nova arquitetura.

HPA/metrics-server e automacao BDD no CI continuam separados deste trabalho.
Nao ha coletor OTLP extra nem dependencia de AWS.

## Verificacao local da integracao

Nesta implementacao, com os agentes habilitados:

- As tres APIs confirmaram conexao HTTPS com o collector do New Relic.
- Os tres pods de monitoramento ficaram Running/Ready, sem erros de permissao nos scrapers.
- Health, readiness e Swagger responderam HTTP 200 nos tres servicos.
- Passaram 545 testes .NET, sem ignorados, e 91 testes Python dos scripts/manifestos.
- Cobertura: Ordens 94,88%, Execucao 97,50% e Cobranca 93,49%.
- Os tres BDDs passaram no kind: entrega, recusa e cancelamento com estorno.
- Uma mensagem real de teste continha newrelic, traceparent e tracestate, com traceparent W3C valido.

O teste da mensagem pausou brevemente somente o consumidor de Execucao, nao
confirmou nem apagou a mensagem e restaurou a replica original. A Saga depois
chegou a RegistroConfirmado. Os dados ficticios continuam no laboratorio.

Essas evidencias confirmam funcionamento local e conexao dos agentes, nao uma
inspecao visual do site. A visualizacao das entidades/traces no New Relic ainda
deve ser conferida na conta. A nova alteracao tambem precisa de PR/CI/Sonar;
nenhuma nova analise Sonar foi enviada durante os testes locais desta etapa.

## Desabilitar sem apagar dados

Na raiz de infra-local:

```bash
python3 scripts/configure_newrelic.py --disable
python3 scripts/deploy_observability.py
```

Depois publique cada servico novamente para reiniciar suas APIs com profiling
desabilitado. Somente mudar o arquivo nao altera processos que ja estao rodando.
Isso remove os agentes Helm, mas nao bancos, filas ou volumes. Nao use destroy
do cluster para desligar apenas o monitoramento.

## Fontes oficiais

- [Agente .NET e versao fixada](https://docs.newrelic.com/docs/release-notes/agent-release-notes/net-release-notes/net-agent-10-57-0/)
- [Tracing distribuido](https://docs.newrelic.com/docs/apm/agents/net-agent/configuration/distributed-tracing-net-agent/)
- [Instrumentacao XML](https://docs.newrelic.com/docs/apm/agents/net-agent/custom-instrumentation/create-transactions-xml-net/)
- [Integracao SQS do agente](https://github.com/newrelic/newrelic-dotnet-agent/blob/main/src/Agent/NewRelic/Agent/Extensions/Providers/Wrapper/AwsSdk/RequestHandlers/SQSRequestHandler.cs)
- [Chart nri-bundle](https://github.com/newrelic/helm-charts/tree/master/charts/nri-bundle)
