# Embasamento teórico das recomendações do FinPlan

As fontes abaixo foram abertas e conferidas. Antes de citar no trabalho, confirme páginas e ano na
própria fonte (a coluna "Conferir" indica o que ainda precisa de olhar).

## 1. Recomendação → fonte

| Recomendação (Simulação) | Fonte | O que a fonte afirma | Aderência | Conferir |
|---|---|---|---|---|
| Guardar mais por mês | Thaler e Benartzi (2004) | Empregados que se comprometeram antecipadamente a poupar parte de aumentos futuros elevaram a taxa média de poupança de 3,5% para 13,6% em 40 meses (78% aderiram) | Por analogia (o estudo é sobre previdência) | — |
| Guardar mais por mês | CVM (2014), passo 5 | Para cada objetivo, estimar custo, prazo e o valor mensal a poupar | Direta | Página 12 (conferida) |
| Gastar menos | CVM (2014), passo 2 | Registrar despesas, separar essenciais e não essenciais, identificar as não essenciais que podem ser cortadas | Direta | Páginas 6 e 7 (conferidas) |
| Gastar menos | Warren e Tyagi (2005) | Regra 50/30/20: necessidades (não podem ser adiadas), desejos (não essenciais) e poupança/dívidas | Direta (classificação essencial × não essencial) | Ano conferido: 2005 |
| Esperar um pouco mais | CVM (2014), passo 5 | Objetivo = custo + prazo + valor mensal; prazo maior reduz o valor mensal | Direta | Páginas 12 e 13 (conferidas) |
| Esperar um pouco mais | Locke e Latham (2002) | Metas específicas e difíceis superam "faça o seu melhor"; meta + feedback é mais eficaz que meta sozinha; prazos folgados tendem a reduzir o ritmo | Por analogia (teoria geral de metas, não de finanças) | — |
| Fazer o dinheiro render | CVM (2014), conclusão | Investimento adequado ao prazo, à liquidez e ao perfil de risco; curto prazo não deve usar produtos de longo prazo; usar estimativa realista de juros | Direta | Páginas 14 e 15 (conferidas) |

## 2. Referências (ABNT)

COMISSÃO DE VALORES MOBILIÁRIOS (Brasil). **Guia CVM de planejamento financeiro**. 1. ed. Rio de Janeiro: CVM, 2014. Disponível em: https://www.gov.br/investidor/pt-br/educacional/publicacoes-educacionais/guias/guia-de-planejamento-financeiro/guia-planejamento-financeiro.pdf

LOCKE, E. A.; LATHAM, G. P. Building a practically useful theory of goal setting and task motivation: a 35-year odyssey. **American Psychologist**, v. 57, n. 9, p. 705-717, 2002. DOI: 10.1037/0003-066X.57.9.705

THALER, R. H.; BENARTZI, S. Save More Tomorrow™: using behavioral economics to increase employee saving. **Journal of Political Economy**, v. 112, n. S1, p. S164-S187, 2004.

WARREN, E.; TYAGI, A. W. **All your worth**: the ultimate lifetime money plan. New York: Free Press, 2005.

## 3. O que NÃO tem fonte (decisão de modelagem, assumir como tal)

- Agrupar despesas não essenciais por variação mensal (K-means) e cortar primeiro as mais variáveis.
- Limite de 50% de corte por item e de 30% do total flexível.
- Limiares de cobertura (110% e 100%) e peso 2 para o esforço de cortar despesas.
- Pesos do ranking (70% esforço, 30% atraso) e as taxas de rendimento (ilustrativas).

Na seção 3 do trabalho, apresente esses itens como **parâmetros do modelo, editáveis e justificados pela
lógica do problema**, e use a validação (sensibilidade) para mostrar o quanto o resultado depende deles.

## 4. Fontes ainda não verificadas (não citar sem abrir)

- Caderno de Educação Financeira do Banco Central (Gestão de Finanças Pessoais): o PDF encontrado não
  permitiu confirmar título, ano nem conteúdo.
- O'Brien e Marakas (2013) e Stair e Reynolds (2005): conferir nos capítulos de SAD o trecho sobre análise
  what-if, busca de meta (goal-seeking) e análise de sensibilidade, para embasar a Simulação.

## 5. Sobre "o e se eu mudasse são variáveis independentes?"

- Como **entradas do modelo**, sim: cada controle é ajustado separadamente e a saída (saldo projetado e
  cobertura) é a variável dependente.
- Entre si, **não são totalmente independentes**:
  - "Aumentar o aporte" e "reduzir despesas" são **substitutos**: os dois viram dinheiro guardado por mês.
  - O rendimento **interage** com o aporte: os juros também rendem sobre o aporte extra, então o efeito
    das três mudanças juntas é maior que a soma dos efeitos isolados (a diferença é a "interação").
  - O limite do aporte (sobra mensal) vale para aporte + aumento; o corte não entra nessa conta porque libera
    o mesmo valor que acrescenta.
