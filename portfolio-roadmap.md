# Portfolio Roadmap — Luca Rivitti (lucanap98)

Atualizado em 15/07/2026. Formato inspirado no padrão de workplan de TAS da GT: cada item tem tarefa, entregável e o que ele viabiliza — não só "o que é", mas "o que passa a ser possível depois de pronto".

Duas trilhas paralelas: **Track 1 — Módulos de análise** (as ferramentas em si) e **Track 2 — Plataforma** (a interface que torna os módulos usáveis sem Python).

---

## Track 1 — Módulos de análise

| # | Item | Tarefa | Entregável | O que viabiliza |
|---|---|---|---|---|
| 1 | **Financial-Model-Validator** ✅ SHIPPED | Checks automáticos de integridade em modelos de projeção (EBITDA bridge, balance sheet tie, cash continuity, tax/depreciation assumptions, outliers). | Repo com `model_validator.py`, `sample_model.py`, README completo. Demo com 5 erros seedados, todos capturados. | Primeiro módulo candidato a entrar na plataforma (Fase 1 da Track 2) — já tem input (planilha) → output (relatório de findings) bem definidos. |
| 2 | **Financial-Analysis** ✅ SHIPPED | CLI de análise de demonstrações financeiras (ROE, margem EBITDA, dívida líquida/EBITDA, ciclo de conversão de caixa, FCF). | Repo com `analisador.py`, README, template Excel. Anterior à framing de pipeline de DD. | Segundo módulo candidato à plataforma. Cobre a etapa de leitura inicial de demonstrações, antes de qualquer valuation. |
| 3 | **DCF parametrizável** ✅ SHIPPED | Modelo de fluxo de caixa descontado com premissas parametrizáveis (WACC, terminal growth ou exit multiple, período explícito de 5 anos) a partir de inputs do usuário. | Repo `Parametrized-DCF` com `dcf_model.py`, `sample_company.py`, README. Suporta Gordon growth e exit multiple, tabela de sensibilidade 5x5, valida WACC > g e falha com erro claro em input incompleto. | Peça central do pipeline de DD para PMEs — gera valuation base para comparação com outros módulos (comps, red flags). Mesmo formato de input do validator (linhas = itens, colunas = período), de propósito, para a plataforma reaproveitar. |
| 4 | **Comps checker** — reposicionado como add-on | Usuário informa os múltiplos que já tem (planilha própria); o sistema calcula a média/mediana do conjunto e sinaliza se cada múltiplo individual faz sentido dentro dele — não busca dados de mercado sozinho. | Repo novo com script de comparação, README, planilha-exemplo. | Cross-check do múltiplo implícito pelo DCF (item 3) contra os comps do próprio usuário. Vendável separadamente como add-on da Track 2 (Fase 4), não como módulo core do pipeline. |
| 5 | **Accretion-dilution calculator** | Calcula impacto de uma transação (M&A) no EPS pro forma do comprador. | Repo com script de cálculo accretion/dilution, README, cenário-exemplo. | Módulo de análise pós-transação — complementa o DCF no ciclo de avaliação de uma operação. |
| 6 | **EBITDA normalizer** | Identifica e ajusta itens não recorrentes/não operacionais no EBITDA reportado (add-backs, despesas de sócio, itens extraordinários). | Repo com lógica de normalização, README, checklist de add-backs comuns em PME brasileira. | Um dos três módulos-núcleo do pipeline de DD para PMEs — alimenta o DCF com EBITDA normalizado em vez do reportado. |
| 7 | **Accounting red flags detector** (estilo Beneish) | Aplica indicadores tipo Beneish M-Score e heurísticas correlatas para sinalizar risco de manipulação contábil. | Repo com script de scoring, README explicando cada índice usado. | Terceiro módulo-núcleo do pipeline de DD — funciona como triagem de risco antes de aprofundar due diligence qualitativa. |
| 8 | **LBO simplified model** | Modelo simplificado de leveraged buyout (estrutura de dívida, retorno ao equity, IRR/MOIC). | Repo com engine de LBO, README, cenário-exemplo. | Módulo de avaliação de viabilidade de aquisição alavancada — fecha o conjunto de ferramentas de valuation do portfólio. |

**Decisão resolvida (15/07/2026):** DCF entra antes do comps checker. Três motivos: (1) narrativa — DCF, EBITDA normalizer e red flags detector formam o trio do "pipeline de DD para PMEs", o diferencial do portfólio; comps checker fica de fora desse trio. (2) Diversidade de portfólio — Financial-Model-Validator já demonstra o padrão "flagar divergências"; DCF mostra uma competência diferente (modelagem de valuation), o que agrega mais ao portfólio do que outro checker. (3) Sequência mais forte — comps checker faz mais sentido como companion do DCF (cross-check do múltiplo implícito contra comps de mercado) do que como ferramenta standalone antes do DCF existir.

**Atualização (15/07/2026):** comps checker reposicionado — vira add-on vendável (usuário insere os múltiplos que já tem, sistema calcula média/mediana e sinaliza divergência dentro do próprio conjunto), não mais um módulo core da fila. Ver Track 2, Fase 4.

---

## Track 2 — Plataforma

| Fase | Item | Tarefa | Entregável | O que viabiliza |
|---|---|---|---|---|
| 1 | **MVP wrapper** | Montar uma interface web mínima com os módulos já prontos (Financial-Model-Validator, Financial-Analysis) como cartões selecionáveis: usuário escolhe o módulo, sobe a planilha, recebe o relatório. Stack recomendada: Streamlit (Python puro, sem front/back separado, deploy grátis via Streamlit Community Cloud). | App funcional publicado em um link, repo próprio (`portfolio-platform` ou similar), documentação de como rodar localmente. | Valida a experiência "sem precisar saber Python" com o menor esforço possível. Serve de demo interna na GT antes de qualquer investimento em arquitetura de plugin. |
| 2 | **Contrato de módulo/plugin** | Só depois de ter 3-4 módulos reais rodando no MVP: definir a interface padrão que todo módulo precisa seguir (manifest com nome, descrição, schema de input esperado, função de entrada padronizada). Refatorar os módulos existentes para essa interface. | Spec do contrato (documento + classe-base ou schema JSON), módulos 1 e 2 adaptados como referência. | Adicionar um repo novo à plataforma passa a ser "escrever um adapter + manifest", sem tocar no núcleo do sistema — portfólio literalmente plugável. |
| 3 | **Orquestração / cadência** | Encadear múltiplos módulos numa sequência definida por caso/engagement (ex: validator → ratio analysis → DCF), com o output de uma etapa alimentando a próxima automaticamente. | Engine de pipeline (define ordem, repassa outputs entre módulos) + UI de acompanhamento de progresso da cadência. | Usuário sobe a planilha uma vez e recebe o resultado do pipeline de DD completo, não módulo por módulo — é a materialização da "cadência automática de análises". |
| 4 | **Empacotamento / distribuição** | Autenticação, controle de acesso por módulo ou pacote (ex: "pacote DD PME" = DCF + normalizer + red flags), infraestrutura de deploy mais robusta que o MVP. Comps checker entra aqui como add-on avulso (usuário insere múltiplos próprios, sistema calcula média/mediana e sinaliza divergência), vendável separado do pacote core. | App com login, seleção de pacote/add-ons, billing (se for vender), hospedagem dedicada. | Distribuição como produto fechado via link — uso externo (GT ou terceiros) sem expor código-fonte. Fase de "vender", não de "construir". |

---

## Princípios de execução (consolidados de conversas anteriores)

- Um item ativo por vez (módulo ou fase de plataforma), ritmo de ~3 sessões por item (skeleton → edge cases → README/polish)
- Escopo v1 enxuto — evitar overbuilding; a Fase 2 da plataforma (contrato de plugin) só começa depois de haver módulos suficientes para saber que forma o contrato precisa ter
- Fontes de dados públicas como padrão (yfinance para tickers internacionais, brapi/B3 para empresas brasileiras, APIs públicas de CNPJ/CND/CEIS-CNEP para diligência); terminal Bloomberg/FactSet como bônus quando disponível
- Critério de priorização: interesse pessoal + potencial de compartilhamento na GT

## Item pendente de manutenção

README do `Financial-Model-Validator` linkava para um repo inexistente (`financial-statement-analyzer`) — corrigido para apontar para `Financial-Analysis`. Versão corrigida entregue em sessão anterior.
