"""Gera lançamentos simulados da persona (24 meses) em data/lancamentos.csv.

Colunas: data, tipo (receita|despesa), categoria, subcategoria, valor, essencial.
Os valores do último mês batem com a persona: renda R$ 6.200 e despesas R$ 4.350.
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
MESES = 24
FIM = "2026-10-01"  # último mês da série (outubro/2026)

# Subcategorias essenciais (não entram nos cortes sugeridos pelo sistema)
ESSENCIAIS = {"Aluguel", "Condomínio", "Energia, água e internet", "Mercado",
              "Saúde", "Manutenção", "Combustível e apps"}

# categoria, subcategoria, valor-base do último mês, volatilidade relativa
DESPESAS = [
    ("Moradia", "Aluguel", 1200, 0.00),
    ("Moradia", "Condomínio", 300, 0.02),
    ("Moradia", "Energia, água e internet", 150, 0.12),
    ("Alimentação", "Mercado", 800, 0.06),
    ("Alimentação", "Delivery e restaurantes", 330, 0.30),
    ("Transporte", "Combustível e apps", 500, 0.15),
    ("Transporte", "Manutenção", 200, 0.60),
    ("Lazer", "Streaming", 60, 0.00),
    ("Lazer", "Saídas", 300, 0.30),
    ("Lazer", "Hobbies", 160, 0.40),
    ("Outros", "Saúde", 150, 0.45),
    ("Outros", "Compras", 200, 0.50),
]
RENDA_BASE = 6200
CRESCIMENTO_MENSAL = 0.003  # tendência leve de alta nas despesas e na renda


def gerar(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    datas = pd.date_range(end=FIM, periods=MESES, freq="MS")
    linhas = []
    for k, data in enumerate(datas):
        atraso = MESES - 1 - k  # meses antes do último
        fator = (1 - CRESCIMENTO_MENSAL) ** atraso
        if k == MESES - 1:  # último mês fecha exatamente com a persona
            linhas.append((data, "receita", "Salário", "Salário", RENDA_BASE))
            for cat, sub, base, _ in DESPESAS:
                linhas.append((data, "despesa", cat, sub, base))
            continue
        renda = RENDA_BASE * fator
        linhas.append((data, "receita", "Salário", "Salário", round(renda, 2)))
        for cat, sub, base, vol in DESPESAS:
            ruido = rng.normal(0, vol)
            valor = max(0.0, base * fator * (1 + ruido))
            linhas.append((data, "despesa", cat, sub, round(valor, 2)))
    out = pd.DataFrame(
        linhas, columns=["data", "tipo", "categoria", "subcategoria", "valor"]
    )
    out["essencial"] = out["subcategoria"].isin(ESSENCIAIS)
    return out


if __name__ == "__main__":
    destino = Path(__file__).parent / "data"
    destino.mkdir(exist_ok=True)
    df = gerar()
    df.to_csv(destino / "lancamentos.csv", index=False)
    print(f"{len(df)} lançamentos gravados em {destino / 'lancamentos.csv'}")
