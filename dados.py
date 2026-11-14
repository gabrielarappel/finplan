"""Persistência simples (JSON e CSV) do perfil, das metas e importação de lançamentos."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pandas as pd

PASTA = Path(__file__).parent / "data"
PERFIL_PADRAO = {"saldo_base": 12480.0, "data_base": "2026-10-31"}
METAS_PADRAO = [
    {"nome": "Reserva de emergência", "valor": 12000.0, "guardado": 8160.0, "prazo": 6, "aporte": 0.0},
    {"nome": "Viagem", "valor": 24000.0, "guardado": 6300.0, "prazo": 12, "aporte": 1200.0},
    {"nome": "Notebook novo", "valor": 5000.0, "guardado": 4250.0, "prazo": 3, "aporte": 0.0},
]
COLUNAS = ["data", "tipo", "categoria", "subcategoria", "valor"]
MODELO_CSV = (
    "data,tipo,categoria,subcategoria,valor\n"
    "2026-11-05,receita,Salário,Salário,6200.00\n"
    "2026-11-06,despesa,Moradia,Aluguel,1200.00\n"
    "2026-11-08,despesa,Alimentação,Mercado,350.50\n"
)


# ------------------------------------------------------------------ JSON simples
def _ler(nome: str, padrao, pasta) -> object:
    try:
        return json.loads((Path(pasta) / nome).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return json.loads(json.dumps(padrao))  # cópia independente do padrão


def _gravar(nome: str, conteudo, pasta) -> None:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome).write_text(json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8")


def carregar_perfil(pasta=PASTA) -> dict:
    return _ler("perfil.json", PERFIL_PADRAO, pasta)


def salvar_perfil(perfil: dict, pasta=PASTA) -> None:
    _gravar("perfil.json", perfil, pasta)


def carregar_metas(pasta=PASTA) -> list[dict]:
    return _ler("metas.json", METAS_PADRAO, pasta)


def salvar_metas(metas: list[dict], pasta=PASTA) -> None:
    _gravar("metas.json", metas, pasta)


def restaurar(pasta=PASTA) -> None:
    for nome in ("perfil.json", "metas.json"):
        (Path(pasta) / nome).unlink(missing_ok=True)


# ------------------------------------------------------------------------ saldo
def saldo_atual(df: pd.DataFrame, perfil: dict) -> float:
    """Saldo informado (no fim do dia `data_base`) + receitas − despesas lançadas depois."""
    apos = df[pd.to_datetime(df["data"]) > pd.Timestamp(perfil["data_base"])]
    rec = apos.loc[apos["tipo"] == "receita", "valor"].sum()
    desp = apos.loc[apos["tipo"] == "despesa", "valor"].sum()
    return float(perfil["saldo_base"] + rec - desp)


# ------------------------------------------------------------------------ metas
def _vazio(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x)) or (isinstance(x, str) and not x.strip())


def validar_metas(linhas: list[dict]) -> tuple[list[dict], list[str]]:
    """Valida as linhas do editor de metas. Linhas totalmente vazias são ignoradas."""
    validas, erros, vistos = [], [], set()
    for i, l in enumerate(linhas, start=1):
        if all(_vazio(l.get(c)) for c in ("nome", "valor", "guardado", "prazo", "aporte")):
            continue
        nome = "" if _vazio(l.get("nome")) else str(l["nome"]).strip()
        try:
            valor = float(l.get("valor"))
            guardado = 0.0 if _vazio(l.get("guardado")) else float(l.get("guardado"))
            prazo = int(float(l.get("prazo")))
            aporte = 0.0 if _vazio(l.get("aporte")) else float(l.get("aporte"))
        except (TypeError, ValueError):
            erros.append(f"Linha {i}: preencha valor desejado e prazo com números.")
            continue
        if not nome:
            erros.append(f"Linha {i}: informe o nome da meta.")
        elif nome in vistos:
            erros.append(f"Linha {i}: já existe uma meta chamada '{nome}'.")
        elif valor <= 0 or prazo < 1 or guardado < 0 or aporte < 0:
            erros.append(f"Linha {i} ('{nome}'): valor e prazo devem ser positivos; guardado e aporte, zero ou mais.")
        else:
            vistos.add(nome)
            validas.append({"nome": nome, "valor": valor, "guardado": guardado, "prazo": prazo, "aporte": aporte})
    if not validas and not erros:
        erros.append("Mantenha ao menos uma meta.")
    return validas, erros


# ----------------------------------------------------------------- importação CSV
def _num(x) -> float:
    s = re.sub(r"[^\d,.\-]", "", str(x))
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def validar_importacao(raw: pd.DataFrame, essenciais: set) -> tuple[pd.DataFrame | None, list[str]]:
    """Valida um CSV de lançamentos. Devolve (dataframe limpo, erros); com erros, o dataframe é None."""
    df = raw.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    faltam = [c for c in COLUNAS if c not in df.columns]
    if faltam:
        return None, [f"Faltam as colunas: {', '.join(faltam)}."]
    if df.empty:
        return None, ["O arquivo não tem linhas."]
    erros = []
    df["tipo"] = df["tipo"].astype(str).str.strip().str.lower()
    # datas ISO (2026-11-06) ou brasileiras (06/11/2026), cada uma com formato explícito, sem ambiguidade
    iso = pd.to_datetime(df["data"], format="ISO8601", errors="coerce")
    br = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")
    df["data"] = iso.fillna(br)
    df["valor"] = df["valor"].map(_num)
    for col in ("categoria", "subcategoria"):
        df[col] = df[col].fillna("").astype(str).str.strip()
    rec = df["tipo"] == "receita"
    df.loc[rec & (df["categoria"] == ""), "categoria"] = "Salário"
    df.loc[rec & (df["subcategoria"] == ""), "subcategoria"] = "Salário"
    ruins = {
        "tipo diferente de receita/despesa": ~df["tipo"].isin(["receita", "despesa"]),
        "data inválida": df["data"].isna(),
        "valor inválido ou não positivo": ~(df["valor"] > 0),
        "categoria ou subcategoria vazia": (df["categoria"] == "") | (df["subcategoria"] == ""),
    }
    for motivo, mask in ruins.items():
        if mask.any():
            linhas = ", ".join(str(i + 2) for i in df.index[mask][:5])  # +2: cabeçalho e base 1
            mais = "…" if mask.sum() > 5 else ""
            erros.append(f"{int(mask.sum())} linha(s) com {motivo} (ex.: linhas {linhas}{mais}).")
    if erros:
        return None, erros
    if "essencial" in df.columns:
        df["essencial"] = df["essencial"].astype(str).str.strip().str.lower().isin(["1", "true", "sim", "s", "verdadeiro"])
    else:
        df["essencial"] = df["subcategoria"].isin(essenciais)
    df.loc[rec, "essencial"] = False
    return df[COLUNAS + ["essencial"]].reset_index(drop=True), []
