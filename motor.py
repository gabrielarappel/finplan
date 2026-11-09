"""Motor analítico e de decisão do FinPlan.

Funções analíticas: sumarizar, projetar_sobra (regressão), classificar (regras),
agrupar_despesas (essenciais + K-means nas discricionárias). Modelo de decisão: gerar_alternativas e recomendar.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression

LIMIAR_FOLGA = 1.10  # cobertura >= 110% -> viável com folga
LIMIAR_VIAVEL = 1.00  # cobertura >= 100% -> viável no limite
CORTE_MAXIMO = 0.30  # máximo de corte aceito no grupo flexível
PESOS_PADRAO = (0.7, 0.3)  # (esforço, atraso)
PESO_CORTE = 2.0  # cortar consumo pesa mais que usar a folga ociosa


# ---------------------------------------------------------------- sumarização
def sumarizar(df: pd.DataFrame, aporte_atual: float = 0.0) -> dict:
    """Diagnóstico do último mês: receitas, despesas, sobra e taxa de poupança."""
    df = df.copy()
    df["mes"] = pd.to_datetime(df["data"]).dt.to_period("M")
    ultimo = df["mes"].max()
    mes = df[df["mes"] == ultimo]
    receitas = mes.loc[mes["tipo"] == "receita", "valor"].sum()
    despesas = mes.loc[mes["tipo"] == "despesa", "valor"].sum()
    sobra = receitas - despesas
    return {
        "mes": str(ultimo),
        "receitas": receitas,
        "despesas": despesas,
        "sobra": sobra,
        "taxa_poupanca": sobra / receitas if receitas else 0.0,
        "folga": sobra - aporte_atual,
        "por_categoria": (
            mes[mes["tipo"] == "despesa"].groupby("categoria")["valor"].sum()
            .sort_values(ascending=False)
        ),
    }


def serie_mensal(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["mes"] = pd.to_datetime(df["data"]).dt.to_period("M")
    s = df.pivot_table(index="mes", columns="tipo", values="valor", aggfunc="sum")
    s["sobra"] = s["receita"] - s["despesa"]
    return s


# ------------------------------------------------------------------ regressão
def projetar_sobra(df: pd.DataFrame, horizonte: int = 12) -> dict:
    """Regressão linear da sobra mensal; devolve a previsão dos próximos meses."""
    s = serie_mensal(df)
    X = np.arange(len(s)).reshape(-1, 1)
    modelo = LinearRegression().fit(X, s["sobra"].values)
    futuro = np.arange(len(s), len(s) + horizonte).reshape(-1, 1)
    return {
        "previsao": modelo.predict(futuro),
        "inclinacao": float(modelo.coef_[0]),
        "r2": float(modelo.score(X, s["sobra"].values)),
    }


# ----------------------------------------------------------------- classificação
def classificar(cobertura: float) -> str:
    if cobertura >= LIMIAR_FOLGA:
        return "viável com folga"
    if cobertura >= LIMIAR_VIAVEL:
        return "viável no limite"
    return "inviável"


# ------------------------------------------------------------------ agrupamento
def agrupar_despesas(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Agrupa as subcategorias de despesa em três grupos.

    - essencial: marcada como essencial nos dados (nunca entra em cortes);
    - variável / estável: K-means (k=2) sobre (média mensal, coeficiente de variação)
      das discricionárias, com entradas padronizadas. O grupo de maior variação
      ('variável') é o primeiro candidato a corte.
    """
    d = df[df["tipo"] == "despesa"].copy()
    d["mes"] = pd.to_datetime(d["data"]).dt.to_period("M")
    ess = d.groupby(["categoria", "subcategoria"])["essencial"].first()
    m = d.pivot_table(index="mes", columns=["categoria", "subcategoria"],
                      values="valor", aggfunc="sum").fillna(0)
    stats = pd.DataFrame({"media": m.mean(), "cv": m.std() / m.mean()}).reset_index()
    stats["essencial"] = [bool(ess[(c, s)]) for c, s in zip(stats["categoria"], stats["subcategoria"])]
    stats["grupo"] = "essencial"
    disc = stats[~stats["essencial"]]
    z = (disc[["media", "cv"]] - disc[["media", "cv"]].mean()) / disc[["media", "cv"]].std()
    cl = KMeans(n_clusters=2, n_init=10, random_state=seed).fit_predict(z)
    cv_medio = disc.groupby(cl)["cv"].mean()
    nome = {cv_medio.idxmax(): "variável", cv_medio.idxmin(): "estável"}
    stats.loc[disc.index, "grupo"] = [nome[c] for c in cl]
    return stats


def total_flexivel(grupos: pd.DataFrame) -> float:
    """Soma mensal das despesas discricionárias (onde cortes são permitidos)."""
    return float(grupos.loc[~grupos["essencial"], "media"].sum())


# ------------------------------------------------------- modelo de decisão
def valor_futuro(inicial: float, aporte: float, meses: int, taxa: float = 0.0) -> float:
    if taxa == 0:
        return inicial + aporte * meses
    f = (1 + taxa) ** meses
    return inicial * f + aporte * (f - 1) / taxa


def aporte_necessario(meta: float, inicial: float, meses: int, taxa: float = 0.0) -> float:
    if taxa == 0:
        return max(0.0, (meta - inicial) / meses)
    f = (1 + taxa) ** meses
    return max(0.0, (meta - inicial * f) * taxa / (f - 1))


def prazo_necessario(meta: float, inicial: float, aporte: float, taxa: float = 0.0) -> int:
    if aporte <= 0:
        raise ValueError("aporte deve ser positivo")
    n = 0
    while valor_futuro(inicial, aporte, n, taxa) < meta - 1e-9:
        n += 1
        if n > 1200:
            raise ValueError("meta inalcançável")
    return n


@dataclass
class Alternativa:
    tipo: str
    descricao: str
    aporte: float
    prazo: int
    esforco: float  # % da renda
    atraso: int  # meses além do prazo desejado
    viavel: bool
    motivo: str
    nota: float = 0.0
    detalhe: dict = field(default_factory=dict)


@dataclass
class Cenario:
    meta: float
    guardado: float
    prazo: int
    aporte_atual: float
    receitas: float
    sobra: float
    flexivel_total: float
    taxas: dict = field(default_factory=lambda: {"poupança": 0.005, "renda fixa": 0.008})


def avaliar(c: Cenario, taxa: float = 0.0) -> dict:
    saldo = valor_futuro(c.guardado, c.aporte_atual, c.prazo, taxa)
    cob = saldo / c.meta
    return {"saldo_projetado": saldo, "cobertura": cob, "veredito": classificar(cob)}


def gerar_alternativas(c: Cenario, pesos=PESOS_PADRAO) -> list[Alternativa]:
    alts: list[Alternativa] = []
    folga = c.sobra - c.aporte_atual

    # 1) aumentar aporte (sem rendimento)
    ap = aporte_necessario(c.meta, c.guardado, c.prazo)
    extra = ap - c.aporte_atual
    ok = ap <= c.sobra
    alts.append(Alternativa(
        "aporte", f"Aumentar o aporte para R$ {ap:,.2f}/mês", ap, c.prazo,
        max(0.0, extra) / c.receitas, 0, ok,
        f"cabe na folga de R$ {folga:,.2f}" if ok else "excede a sobra mensal",
        detalhe={"extra": extra}))

    # 2) reduzir despesas flexíveis para liberar o valor faltante
    falta = max(0.0, ap - c.aporte_atual)
    pct = falta / c.flexivel_total if c.flexivel_total else math.inf
    ok = pct <= CORTE_MAXIMO
    alts.append(Alternativa(
        "despesas", f"Cortar {pct:.1%} das despesas flexíveis (R$ {falta:,.2f}/mês)",
        ap, c.prazo, PESO_CORTE * falta / c.receitas, 0, ok,
        "dentro do corte máximo" if ok else f"acima do corte máximo de {CORTE_MAXIMO:.0%}",
        detalhe={"corte_pct": pct, "valor": falta}))

    # 3) estender prazo mantendo o aporte atual
    if c.aporte_atual > 0:
        n = prazo_necessario(c.meta, c.guardado, c.aporte_atual)
        alts.append(Alternativa(
            "prazo", f"Estender o prazo para {n} meses", c.aporte_atual, n,
            0.0, max(0, n - c.prazo), True,
            "mantém o aporte atual", detalhe={"meses_extra": n - c.prazo}))

    # 4) aplicar o dinheiro (aporte necessário com rendimento)
    for nome, taxa in c.taxas.items():
        ap_r = aporte_necessario(c.meta, c.guardado, c.prazo, taxa)
        ok = ap_r <= c.sobra
        alts.append(Alternativa(
            "aplicação", f"Aplicar em {nome} ({taxa:.2%} a.m.): aporte de R$ {ap_r:,.2f}/mês",
            ap_r, c.prazo, max(0.0, ap_r - c.aporte_atual) / c.receitas, 0, ok,
            "taxa ilustrativa, editável", detalhe={"taxa": taxa}))

    # esforço = valor extra mobilizado por mês / renda (corte de despesas pesa PESO_CORTE)
    # nota ponderada (menor = melhor): esforço normalizado + atraso normalizado
    max_esf = max(a.esforco for a in alts) or 1
    max_atr = max(a.atraso for a in alts) or 1
    for a in alts:
        a.nota = pesos[0] * a.esforco / max_esf + pesos[1] * a.atraso / max_atr
    return sorted(alts, key=lambda a: (not a.viavel, a.nota))


def recomendar(c: Cenario, pesos=PESOS_PADRAO) -> dict:
    atual = avaliar(c)
    alts = gerar_alternativas(c, pesos)
    if atual["veredito"] != "inviável":
        return {"atual": atual, "alternativas": alts,
                "texto": "A meta já é viável com o aporte atual; nenhuma mudança é necessária."}
    viaveis = [a for a in alts if a.viavel]
    melhor = viaveis[0] if viaveis else None
    texto = (f"Recomendação: {melhor.descricao}. {melhor.motivo}." if melhor
             else "Nenhuma alternativa isolada viabiliza a meta; considere combinar alavancas.")
    return {"atual": atual, "alternativas": alts, "melhor": melhor, "texto": texto}
