# SonarQube local e qualidade no CI

## Estrutura

Um SonarQube Community compartilhado pelos tres servicos, com PostgreSQL proprio.
Nao faz parte das APIs, nao acessa os bancos da oficina e nao usa AWS/Sonar Cloud.
Somente a interface Sonar e publicada em 127.0.0.1:9000; o PostgreSQL nao publica
porta no computador. Imagens oficiais fixadas por digest e volumes persistentes
preservam projetos, usuarios e historico. Nao delete os volumes para parar.

Na raiz de oficina-mecanica-infra-local, com Docker Desktop aberto:

```bash
docker compose --env-file sonar.env.example -f compose.sonar.yml up -d --wait --wait-timeout 420
```

O env de exemplo tem valores ficticios para o laboratorio. Para personalizar,
use um arquivo .env.sonar, ignorado pelo Git, e troque o argumento --env-file.
Mudar apenas a senha no env nao altera a senha de um PostgreSQL ja inicializado.

Abra http://localhost:9000. Primeiro acesso: admin/admin; altere a senha pedida
pelo Sonar. A senha do usuario Sonar e diferente da senha JDBC do PostgreSQL.

Parar mantendo dados e depois reiniciar:

```bash
docker compose --env-file sonar.env.example -f compose.sonar.yml down
docker compose --env-file sonar.env.example -f compose.sonar.yml up -d --wait --wait-timeout 420
```

## Projetos e tokens

Crie projetos locais/manual, sem importar nem autorizar uma GitHub App:

| Repositorio | Chave do projeto Sonar | Branch principal |
| --- | --- | --- |
| oficina-mecanica-ordens | oficina-mecanica-ordens | main |
| oficina-mecanica-execucao | oficina-mecanica-execucao | main |
| oficina-mecanica-cobranca | oficina-mecanica-cobranca | main |

Em My Account > Security, crie um Project Analysis Token para cada projeto.
Nomes sugeridos: github-actions-ordens, github-actions-execucao e
github-actions-cobranca. Escolha o projeto correto e uma expiracao que cubra a
entrega. O nome do token nao precisa ser igual ao nome do Secret.

Em CADA repositorio GitHub, Settings > Secrets and variables > Actions:

- Repository Secret SONAR_TOKEN: valor do token daquele projeto.
- Repository Variable SONAR_HOST_URL: http://127.0.0.1:9000 (opcional, ja e o padrao).

Nunca envie tokens em mensagens, commits ou capturas de tela. Credenciais JDBC,
senha admin e token de analise sao coisas diferentes. Nao use token admin global
quando um token restrito de analise de projeto resolve.

## Analise local manual

Cada repositorio tem scripts/sonar_scan.sh e manifesto de ferramentas fixando o
SonarScanner .NET. Na raiz do servico, em um terminal interativo:

```bash
bash scripts/sonar_scan.sh
```

O script pede o token sem exibi-lo se SONAR_TOKEN nao estiver no ambiente.
O token nao e gravado em arquivo pelo script. Use o token do projeto correto.
SONAR_HOST_URL so aceita loopback HTTP, sem credenciais na URL.

O script cria um projeto Compose de teste com nome unico e portas aleatorias.
Ordens usa SQLite de teste e ElasticMQ; Execucao acrescenta Mongo replica set;
Cobranca acrescenta MySQL. Nenhum deles usa os containers ou dados do ambiente
de desenvolvimento. No final, inclusive em falha, remove somente os containers
e volumes desse projeto temporario de teste.

Fluxo: scanner begin -> build completo -> testes e OpenCover/Cobertura ->
conferir todos os testes executados -> exigir 80% -> scanner end e quality gate.
Relatorios ficam em TestResults/sonar, ignorados pelo Git. Falhas no quality gate
retornam erro: nao sao convertidas em sucesso. Resolver os apontamentos reais
do Sonar e uma etapa posterior a primeira analise, nao remover regras apenas
para deixar o painel verde.

A cobertura inclui as cinco camadas. Exclui somente migrations geradas; em
Cobranca, o executavel de mock de pagamento e ferramenta de teste, fora do
escopo da API analisada. Nao exclui Infrastructure nem regras de negocio.

Para conferir apenas a infraestrutura e os testes, sem token ou envio ao Sonar:

```bash
bash scripts/sonar_scan.sh --somente-testes
```

Esse modo NAO significa que o Sonar aprovou o projeto. BDD distribuido permanece
no guia 14 e nao e executado por este script de analise individual.

## Runner local e seguranca

Os jobs normais de build/testes continuam no GitHub. O novo workflow
qualidade-local.yml usa self-hosted + macOS + sonar-local para acessar o Sonar
do notebook. O computador e Docker precisam estar ligados durante o job.

O runner antigo da Fase 3 nao foi alterado. Como estes repositorios pertencem
a uma conta pessoal, configure um runner por repositorio, em pastas separadas
fora dos repositorios, por exemplo actions-runner-ordens, actions-runner-execucao
e actions-runner-cobranca no Desktop.

Em Settings > Actions > Runners > New self-hosted runner, escolha macOS/ARM64
neste computador. Use o download e a verificacao de hash mostrados pelo GitHub.
Na configuracao de CADA runner, adicione --labels sonar-local,kind-local ao comando
config.sh gerado pelo GitHub e mantenha os labels padrao. O token temporario
desse comando e do GitHub Runner, nao e o SONAR_TOKEN.
Sonar usa sonar-local; o deploy no kind usa kind-local, no mesmo
computador. A [decisao de entrega local](16-kubernetes-local.md) substitui AWS
como destino da Fase 4, sem mudar a entrega das fases anteriores.
Inicie com ./run.sh ou configure o servico pela documentacao do GitHub.
Nao reutilize a mesma pasta/configuracao de runner entre repositorios.

Runners pessoais podem acessar arquivos do computador. A recomendacao oficial
do GitHub e evitar self-hosted em repositorios publicos para codigo nao confiavel.
Por isso, este workflow NAO usa pull_request nem pull_request_target e nunca
busca o codigo de um fork. Nao remova essa protecao nem execute nele PRs externos.
Proteja a main e revise o codigo antes de mesclar. Isso reduz o risco, mas nao
torna um runner pessoal um ambiente isolado para codigo arbitrario.

## Quando o workflow executa

A Community gratuita analisa apenas a branch principal, sem analise/decoracao
nativa de PR. Build, testes e bloqueio de cobertura continuam nos PRs via CI.
Depois de merge, um push na main executa o CI; somente se ele passar,
qualidade-local.yml analisa o SHA exato daquele push na main. Nao testa outra
revisao mais recente por engano. Jobs concorrentes do mesmo servico sao seriados.

Tambem e possivel Actions > Qualidade local > Run workflow, escolhendo main.
Outra branch nao executa o job local. Antes do runner/token estarem configurados,
o workflow ainda nao esta operacional; sem runner compativel ficara na fila.
O check de qualidade e posterior ao merge, nao um gate Sonar de PR.
O CD aguarda esse resultado e consulta novamente o CI e o Sonar do SHA exato.
Falha ou ausencia de qualquer verificacao impede o deploy. Qualidade e CD usam
um lock de arquivo compartilhado no notebook para evitar builds/testes pesados
simultaneos entre os tres runners; os pipelines continuam independentes.

## Estado e proximo teste

Os tres runners e tokens foram configurados. As primeiras analises autenticadas
no GitHub passaram em Ordens, Execucao e Cobranca. Alteracoes futuras precisam
passar novamente: um resultado antigo nao aprova automaticamente outro commit.
O workflow de entrega desta etapa ainda precisa de PR/merge e execucao real.
Veja o [guia de entrega](17-deploy-kubernetes-local.md).

Fontes oficiais:

- https://docs.sonarsource.com/sonarqube-community-build/devops-platform-integration/github-integration/adding-analysis-to-github-actions-workflow
- https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners
- https://docs.github.com/en/actions/reference/security/secure-use
