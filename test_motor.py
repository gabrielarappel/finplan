"""Testes que conferem os números da persona calculados à mão."""
import pytest

import motor
from gerar_dados import gerar

META, GUARDADO, PRAZO, APORTE = 24000, 6300, 12, 1200
RENDA, DESPESAS = 6200, 4350


@pytest.fixture(scope="module")
def df():
    return gerar()


@pytest.fixture
def cenario():
    return motor.Cenario(meta=META, guardado=GUARDADO, prazo=PRAZO, aporte_atual=APORTE,
                         receitas=RENDA, sobra=RENDA - DESPESAS, flexivel_total=1050)


def test_sumarizacao_ultimo_mes(df):
    r = motor.sumarizar(df, aporte_atual=APORTE)
    assert r["receitas"] == RENDA
    assert r["despesas"] == DESPESAS
    assert r["sobra"] == 1850
    assert r["taxa_poupanca"] == pytest.approx(0.2984, abs=1e-4)
    assert r["folga"] == 650
    assert r["por_categoria"]["Moradia"] == 1650


def test_veredito_inviavel(cenario):
    a = motor.avaliar(cenario)
    assert a["saldo_projetado"] == 20700
    assert a["cobertura"] == pytest.approx(0.8625)
    assert a["veredito"] == "inviável"


def test_limiares():
    assert motor.classificar(1.10) == "viável com folga"
    assert motor.classificar(1.00) == "viável no limite"
    assert motor.classificar(0.99) == "inviável"


def test_aporte_necessario_sem_juros():
    assert motor.aporte_necessario(META, GUARDADO, PRAZO) == 1475


def test_aporte_necessario_com_juros():
    assert motor.aporte_necessario(META, GUARDADO, PRAZO, 0.005) == pytest.approx(1403.4, abs=0.1)
    assert motor.aporte_necessario(META, GUARDADO, PRAZO, 0.008) == pytest.approx(1360.8, abs=0.1)


def test_valor_futuro_consistente_com_aporte():
    for taxa in (0.0, 0.005, 0.008):
        ap = motor.aporte_necessario(META, GUARDADO, PRAZO, taxa)
        assert motor.valor_futuro(GUARDADO, ap, PRAZO, taxa) == pytest.approx(META)


def test_prazo_necessario():
    assert motor.prazo_necessario(META, GUARDADO, APORTE) == 15


def test_corte_de_despesas(cenario):
    alts = {a.tipo: a for a in motor.gerar_alternativas(cenario) if a.tipo != "aplicação"}
    assert alts["despesas"].detalhe["corte_pct"] == pytest.approx(275 / 1050)
    assert alts["despesas"].viavel  # 26,2% <= corte máximo de 30%
    assert alts["aporte"].viavel  # R$ 1.475 cabe na sobra de R$ 1.850


def test_recomendacao_da_persona(cenario):
    r = motor.recomendar(cenario)
    assert r["atual"]["veredito"] == "inviável"
    assert r["melhor"].tipo in {"aporte", "aplicação", "prazo"}
    assert r["melhor"].viavel
    viaveis = [a for a in r["alternativas"] if a.viavel]
    assert viaveis[-1].tipo == "despesas"  # cortar consumo é a última opção
    assert "Recomendação" in r["texto"]


def test_regressao_tem_horizonte(df):
    p = motor.projetar_sobra(df, 12)
    assert len(p["previsao"]) == 12
    assert -1 <= p["r2"] <= 1


def test_agrupamento_cobre_todas_subcategorias(df):
    g = motor.agrupar_despesas(df)
    assert len(g) == 12
    assert set(g["grupo"]) <= {"essencial", "estável", "variável"}
    assert (g.loc[g["essencial"], "grupo"] == "essencial").all()
    assert motor.total_flexivel(g) == pytest.approx(1050, abs=40)


def test_cortes_nunca_atingem_essenciais(df):
    g = motor.agrupar_despesas(df)
    assert not g.loc[g["subcategoria"].isin(["Aluguel", "Condomínio", "Mercado"]), "grupo"].isin(["variável", "estável"]).any()
