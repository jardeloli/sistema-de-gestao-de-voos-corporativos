# Sistema de Gestão de Voos Corporativos – Lavronorte

Aplicação web para agendar, registrar e acompanhar os voos corporativos da aeronave da Lavronorte, centralizando finalidade das viagens, passageiros, abastecimentos, custos e histórico de utilização.

Projeto acadêmico da unidade curricular **Programação para Web** – Análise e Desenvolvimento de Sistemas, UNIBALSAS (2026.2).
Equipe: Gustavo Noleto, Jardel Oliveira, Miquéias do Nascimento e Wallaci Araujo.

## Funcionalidades

| Requisito | Onde está na aplicação |
|---|---|
| RF01 Cadastro de usuários | Cadastros › Usuários (somente Administrador) |
| RF02 Cadastro de aeronave | Cadastros › Aeronaves |
| RF03/RF04 Cadastro e agendamento de viagens | Viagens › Agendar viagem |
| RF05 Alteração de viagens | Detalhe da viagem › Alterar (apenas viagens agendadas) |
| RF06 Cancelamento | Detalhe da viagem › Cancelar viagem (o registro fica no histórico) |
| RF07 Controle de custos | Detalhe da viagem › Lançar custo |
| RF08 Controle de abastecimento | Abastecimentos › Registrar abastecimento |
| RF09 Consumo de combustível | Detalhe da viagem › Registrar voo realizado (horas e litros) |
| RF10 Histórico | Viagens › aba Histórico |
| RF11 Viagens agendadas | Tela inicial e Viagens › aba Agendadas |
| RF12 Dashboard gerencial | Indicadores (Administrador e Gestor) |
| RF13 Filtros | Viagens › Filtrar viagens |

### Perfis de acesso

| Perfil | Pode |
|---|---|
| Administrador | Tudo, inclusive usuários e aeronaves |
| Gestor | Indicadores, agendar/alterar/cancelar viagens, lançar custos |
| Agendador | Agendar/alterar/cancelar viagens e cadastrar passageiros |
| Operacional | Registrar voo realizado, abastecimentos e custos |

Todos os perfis consultam a agenda, o histórico, os abastecimentos, as aeronaves e os passageiros.

## Tecnologias

- Python 3.12 e Django 5.2 (padrão MVT)
- HTML, CSS e JavaScript (sem framework de front-end)
- Bootstrap 5.3 e Bootstrap Icons 1.11 (servidos localmente em `static/vendor`)
- Chart.js 4.4 (gráfico do painel de indicadores)
- Fontes B612 e Atkinson Hyperlegible (servidas localmente)
- SQLite em desenvolvimento e PostgreSQL no de produção
- WhiteNoise para servir arquivos estáticos em produção

## Instalação (Windows)

Pré-requisitos: [Python 3.12+](https://www.python.org/downloads/) e Git.

```powershell
git clone https://github.com/jardeloli/Sistema-de-Gest-o-de-Voos-Corporativo-.git
cd Sistema-de-Gest-o-de-Voos-Corporativo-

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
copy .env.example .env

python manage.py migrate
python manage.py popular_demo      # Rode isso caso queira testar com dados ficiticios
python manage.py runserver
```

Acesse http://127.0.0.1:8000.

Em Linux/macOS, troque a ativação por `source .venv/bin/activate` e o `copy` por `cp`.

### Usuários de demonstração

Criados pelo comando `popular_demo` (senha de todos: `voos2026`):

| Usuário | Perfil |
|---|---|
| admin | Administrador (também acessa `/admin`) |
| roberto | Gestor |
| carlos | Agendador |
| marcos | Operacional |

Para recriar os dados do zero: `python manage.py popular_demo --limpar`.

Sem os dados de demonstração, crie o primeiro acesso com `python manage.py createsuperuser`.

### Usando PostgreSQL

No `.env`, defina `DB_ENGINE=postgres` e preencha `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` e `DB_PORT`. Depois rode `python manage.py migrate`.

## Como usar

1. **Agendar** – em *Viagens › Agendar viagem*, informe aeronave, data, horário, origem, destino, passageiros, finalidade e descrição. O sistema impede exceder a capacidade da aeronave e marcar dois voos da mesma aeronave com menos de 2 h de diferença.
2. **Registrar o voo** – depois da viagem, abra o detalhe e use *Registrar voo realizado* para informar horas de voo e combustível consumido. Voos com data passada e sem registro aparecem como *Aguardando registro* na tela inicial.
3. **Lançar abastecimentos e custos** – no detalhe da viagem. O valor total do abastecimento é calculado automaticamente e entra no custo da viagem.
4. **Acompanhar** – em *Indicadores*, escolha o período para ver viagens, horas, consumo, custos, destinos e finalidades.

## Testes

```powershell
python manage.py test apps
```

São 15 testes cobrindo regras de agendamento, cancelamento, cálculo de custos, controle de acesso e abertura de todas as telas.

## Estrutura

```
config/              configurações, URLs raiz e WSGI
apps/
  core_forms.py      mixin que aplica Bootstrap e atributos de acessibilidade aos formulários
  contas/            login, usuários e perfis de acesso (perfis.py define quem pode o quê)
  frota/             aeronaves
  viagens/           viagens, passageiros, custos, abastecimentos e comando popular_demo
  painel/            tela inicial, indicadores, filtros de template e páginas de erro
templates/           templates HTML (base, componentes parciais e telas por app)
static/              CSS e JS próprios e bibliotecas de terceiros (vendor/)
docs/                documentação e capturas de tela
```