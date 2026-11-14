"""Testes do perfil, das metas e da importação de lançamentos."""
import pandas as pd
import pytest

import dados
from gerar_dados import ESSENCIAIS, gerar


@pytest.fixture(scope="module")
def df():
    return gerar()


def test_saldo_atual_soma_lancamentos_depois_da_data_base(df):
    perfil = {"saldo_base": 12480.0, "data_base": "2026-10-31"}
    assert dados.saldo_atual(df, perfil) == 12480.0  # nada depois de 31/10
    extra = pd.DataFrame([
        (pd.Timestamp("2026-11-05"), "receita", "Salário", "Salário", 6200.0, False),
        (pd.Timestamp("2026-11-06"), "despesa", "Moradia", "Aluguel", 1200.0, True),
        (pd.Timestamp("2026-10-31"), "despesa", "Lazer", "Saídas", 999.0, False)], columns=df.columns)
    com = pd.concat([df, extra], ignore_index=True)
    assert dados.saldo_atual(com, perfil) == 12480.0 + 6200.0 - 1200.0  # o de 31/10 não conta


def test_perfil_e_metas_persistem_e_restauram(tmp_path):
    assert dados.carregar_perfil(tmp_path)["saldo_base"] == 12480.0
    dados.salvar_perfil({"saldo_base": 100.0, "data_base": "2026-11-13"}, tmp_path)
    assert dados.carregar_perfil(tmp_path)["saldo_base"] == 100.0
    metas = [{"nome": "X", "valor": 10.0, "guardado": 0.0, "prazo": 2, "aporte": 5.0}]
    dados.salvar_metas(metas, tmp_path)
    assert dados.carregar_metas(tmp_path) == metas
    dados.restaurar(tmp_path)
    assert dados.carregar_perfil(tmp_path)["saldo_base"] == 12480.0
    assert len(dados.carregar_metas(tmp_path)) == 3


def test_padroes_nao_sao_alterados_por_quem_usa(tmp_path):
    m = dados.carregar_metas(tmp_path)
    m[0]["nome"] = "alterado"
    assert dados.carregar_metas(tmp_path)[0]["nome"] == "Reserva de emergência"


def test_validar_metas_ok_e_ignora_linhas_vazias():
    linhas = [{"nome": "Carro", "valor": 30000, "guardado": None, "prazo": 24.0, "aporte": float("nan")},
              {"nome": None, "valor": None, "guardado": None, "prazo": None, "aporte": None}]
    validas, erros = dados.validar_metas(linhas)
    assert not erros and validas == [{"nome": "Carro", "valor": 30000.0, "guardado": 0.0, "prazo": 24, "aporte": 0.0}]


@pytest.mark.parametrize("linha", [
    {"nome": "", "valor": 10, "guardado": 0, "prazo": 3, "aporte": 0},
    {"nome": "A", "valor": 0, "guardado": 0, "prazo": 3, "aporte": 0},
    {"nome": "A", "valor": 10, "guardado": 0, "prazo": 0, "aporte": 0},
    {"nome": "A", "valor": 10, "guardado": -1, "prazo": 3, "aporte": 0},
    {"nome": "A", "valor": "abc", "guardado": 0, "prazo": 3, "aporte": 0}])
def test_validar_metas_rejeita_linhas_invalidas(linha):
    validas, erros = dados.validar_metas([linha])
    assert erros and not validas


def test_validar_metas_rejeita_nome_repetido_e_lista_vazia():
    l = {"nome": "A", "valor": 10, "guardado": 0, "prazo": 3, "aporte": 0}
    assert dados.validar_metas([l, dict(l)])[1]
    assert dados.validar_metas([])[1]


def test_importacao_valida_e_converte():
    raw = pd.DataFrame({"Data": ["05/11/2026", "2026-11-06"], "Tipo": ["Receita", "despesa"],
                        "categoria": ["", "Moradia"], "subcategoria": ["", "Aluguel"],
                        "valor": ["6.200,00", "R$ 1200"]})
    out, erros = dados.validar_importacao(raw, ESSENCIAIS)
    assert not erros
    assert list(out["valor"]) == [6200.0, 1200.0]
    assert out.loc[0, "subcategoria"] == "Salário" and not out.loc[0, "essencial"]
    assert bool(out.loc[1, "essencial"])  # Aluguel é essencial
    assert out["data"].iloc[0] == pd.Timestamp("2026-11-05")


def test_importacao_aponta_erros():
    raw = pd.DataFrame({"data": ["x", "2026-11-06"], "tipo": ["receita", "gasto"],
                        "categoria": ["a", "b"], "subcategoria": ["a", "b"], "valor": ["10", "-5"]})
    out, erros = dados.validar_importacao(raw, ESSENCIAIS)
    assert out is None and len(erros) >= 3
    assert dados.validar_importacao(pd.DataFrame({"data": [1]}), ESSENCIAIS)[1][0].startswith("Faltam")


def test_modelo_csv_e_valido():
    from io import StringIO
    out, erros = dados.validar_importacao(pd.read_csv(StringIO(dados.MODELO_CSV), dtype=str), ESSENCIAIS)
    assert not erros and len(out) == 3
