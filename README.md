# FinPlan — Sistema de Apoio à Decisão para planejamento financeiro pessoal

Protótipo executável (Python + Streamlit). Dados simulados de uma persona (24 meses de lançamentos).

## Executar
```bash
pip install -r requirements.txt
python gerar_dados.py        # gera data/lancamentos.csv (opcional: o app gera sozinho)
streamlit run app.py
```
Login de demonstração: `demo@finplan.app` / `demo123`

## Testes
```bash
pytest -q
```

## Estrutura
- `gerar_dados.py` — gerador de lançamentos simulados (persona: renda R$ 6.200, despesas R$ 4.350).
- `motor.py` — funções analíticas (sumarização, regressão, classificação, agrupamento) e modelo de decisão.
- `app.py` — interface (login, visão geral, lançamentos, meus dados, simulação, relatórios).
- `dados.py` — saldo, metas, importação de CSV e persistência (JSON em `data/`).
- `referencias.py` — base teórica exibida nas recomendações; fontes em `docs/embasamento_teorico.md`.
- `test_motor.py`, `test_dados.py`, `test_app.py` — testes do motor, dos dados e da interface.

## Onde entram os dados
- **Meus dados:** saldo atual (a partir dele o sistema soma receitas e subtrai despesas lançadas depois), metas editáveis e importação de lançamentos por CSV (há um modelo para baixar).
- **Lançamentos:** registro do dia a dia, com opção de criar categoria/subcategoria nova.
- Um mês só entra nas análises depois que a receita dele é lançada.

## Limitações
Dados simulados; rendimento com taxa constante, sem imposto nem inflação; compara cenários de aplicação,
mas não recomenda produtos de investimento.
