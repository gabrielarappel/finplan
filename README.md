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
- `app.py` — interface (login, visão geral, lançamentos, simulação, relatórios).
- `test_motor.py`, `test_app.py` — testes do motor e da interface.

## Limitações
Dados simulados; rendimento com taxa constante, sem imposto nem inflação; compara cenários de aplicação,
mas não recomenda produtos de investimento.
