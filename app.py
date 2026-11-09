"""FinPlan — Sistema de Apoio à Decisão para planejamento financeiro pessoal.

Execução: streamlit run app.py   (login demo: demo@finplan.app / demo123)
"""
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import motor
from gerar_dados import ESSENCIAIS, gerar

CSV = Path(__file__).parent / "data" / "lancamentos.csv"
USUARIO, SENHA = "demo@finplan.app", "demo123"
SALDO_ATUAL = 12480.0

AREIA, AREIA_ESC, TINTA, MUDO = "#F5EEE1", "#EBE0CB", "#2E2B24", "#857C68"
OLIVA, TERRA, OCRE, LINHA = "#5C6B3B", "#C0603A", "#D9A441", "#D8CCB3"
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

st.set_page_config(page_title="FinPlan", page_icon="🌿", layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Figtree:wght@400;500;600&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Figtree', sans-serif; color: {TINTA}; }}
.stApp {{ background: {AREIA}; }}
h1, h2, h3, .serif {{ font-family: 'Fraunces', serif !important; font-weight: 600; letter-spacing: -0.01em; color: {TINTA}; }}
h1 {{ font-size: 2.3rem !important; }}
[data-testid="stSidebar"] {{ background: {AREIA_ESC}; border-right: 1px solid {LINHA}; }}
[data-testid="stHeader"] {{ background: transparent; }}
.card {{ background: #FBF7EE; border: 1px solid {LINHA}; border-radius: 18px 18px 18px 4px; padding: 1.1rem 1.3rem; }}
.big {{ font-family: 'Fraunces', serif; font-size: 1.75rem; font-weight: 600; line-height: 1.15; white-space: nowrap; }}
.lbl {{ color: {MUDO}; font-size: .85rem; }}
.ok {{ color: {OLIVA}; font-weight: 600; }} .bad {{ color: {TERRA}; font-weight: 600; }} .mid {{ color: #9A6B14; font-weight: 600; }}
.bar {{ background: {AREIA_ESC}; border-radius: 99px; height: 10px; overflow: hidden; margin: .3rem 0 .15rem; }}
.bar > div {{ height: 100%; border-radius: 99px; }}
.rec {{ background: {OLIVA}; color: #FBF7EE; border-radius: 99px; padding: 2px 10px; font-size: .75rem; margin-left: .5rem; }}
.grp {{ font-family: 'Fraunces', serif; font-size: 1.15rem; margin: 1rem 0 .3rem; }}
.stButton > button, .stFormSubmitButton > button {{ background: {TERRA}; color: #FBF7EE; border: 0; border-radius: 99px; padding: .45rem 1.4rem; font-weight: 600; }}
.stButton > button:hover, .stFormSubmitButton > button:hover {{ background: #A64E2B; color: #fff; }}
.nota {{ color: {MUDO}; font-size: .82rem; }}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ utilidades
def brl(v: float) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float, casas: int = 1) -> str:
    return f"{v * 100:.{casas}f}".replace(".", ",") + "%"


def rotulo(p: pd.Period) -> str:
    return f"{MESES_PT[p.month - 1]}/{str(p.year)[2:]}"


def barra(frac: float, cor: str = OLIVA) -> str:
    return f'<div class="bar"><div style="width:{min(frac, 1) * 100:.0f}%;background:{cor}"></div></div>'


def estilo(chart: alt.Chart, altura: int = 260) -> alt.Chart:
    return (chart.properties(height=altura).configure(background="rgba(0,0,0,0)")
            .configure_axis(labelColor=MUDO, titleColor=MUDO, gridColor=LINHA, domainColor=LINHA,
                            labelFont="Figtree", titleFont="Figtree")
            .configure_legend(labelColor=TINTA, titleColor=MUDO, orient="top", labelFont="Figtree")
            .configure_view(strokeWidth=0))


def classe(veredito: str) -> str:
    return {"inviável": "bad", "viável no limite": "mid"}.get(veredito, "ok")


def carregar() -> pd.DataFrame:
    if not CSV.exists():
        CSV.parent.mkdir(exist_ok=True)
        gerar().to_csv(CSV, index=False)
    return pd.read_csv(CSV, parse_dates=["data"])


def estado():
    ss = st.session_state
    ss.setdefault("logado", False)
    ss.setdefault("df", carregar())
    ss.setdefault("metas", [
        {"nome": "Reserva de emergência", "valor": 12000.0, "guardado": 8160.0, "prazo": 6, "aporte": 0.0},
        {"nome": "Viagem", "valor": 24000.0, "guardado": 6300.0, "prazo": 12, "aporte": 1200.0},
        {"nome": "Notebook novo", "valor": 5000.0, "guardado": 4250.0, "prazo": 3, "aporte": 0.0},
    ])
    ss.setdefault("taxas", {"poupança": 0.5, "renda fixa": 0.8})  # % a.m., ilustrativas
    ss.setdefault("simulacoes", [])


# ------------------------------------------------------------------------ login
def tela_login():
    esq, dir_ = st.columns([1.2, 1], gap="large")
    with esq:
        st.markdown(f"""
        <div style="padding:3rem 1rem">
        <div class="serif" style="font-size:1.4rem;color:{TERRA}">FinPlan</div>
        <div class="serif" style="font-size:3.2rem;line-height:1.08;margin:1.2rem 0">Quanto falta para chegar lá,<br>e o que muda se eu fizer diferente?</div>
        <div style="color:{MUDO};max-width:30rem">Registre o que entra e o que sai, defina uma meta e compare caminhos
        antes de decidir: guardar mais, gastar menos, esperar um pouco ou aplicar o dinheiro.</div>
        </div>""", unsafe_allow_html=True)
    with dir_:
        st.markdown("<div style='height:4rem'></div>", unsafe_allow_html=True)
        st.markdown("## Entrar")
        with st.form("login"):
            email = st.text_input("E-mail", placeholder="voce@email.com")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                if email.strip().lower() == USUARIO and senha == SENHA:
                    st.session_state.logado = True
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")
        with st.expander("Ainda não tem conta? Criar conta"):
            st.write("Este é um protótipo com uma única conta de demonstração.")
            st.code(f"e-mail: {USUARIO}\nsenha:  {SENHA}")


# -------------------------------------------------------------- dados derivados
def contexto():
    df = st.session_state.df
    resumo = motor.sumarizar(df)
    grupos = motor.agrupar_despesas(df)
    return df, resumo, grupos, motor.total_flexivel(grupos)


# ------------------------------------------------------------------ visão geral
def pagina_geral():
    df, r, grupos, flex = contexto()
    st.markdown("# Visão geral")
    st.caption(f"Referência: {rotulo(pd.Period(r['mes']))}")
    c = st.columns(4)
    cards = [("Saldo atual", brl(SALDO_ATUAL), "todas as contas"),
             ("Entrou no mês", brl(r["receitas"]), ""),
             ("Saiu no mês", brl(r["despesas"]), ""),
             ("Taxa de poupança", pct(r["taxa_poupanca"]), "da renda que sobra")]
    for col, (t, v, s) in zip(c, cards):
        col.markdown(f'<div class="card"><div class="lbl">{t}</div><div class="big">{v}</div>'
                     f'<div class="lbl">{s}</div></div>', unsafe_allow_html=True)
    st.write("")
    a, b = st.columns([1.5, 1], gap="large")
    s = motor.serie_mensal(df).tail(6)
    long = pd.DataFrame({"mes": [rotulo(p) for p in s.index] * 2,
                         "tipo": ["Receitas"] * len(s) + ["Despesas"] * len(s),
                         "valor": list(s["receita"]) + list(s["despesa"])})
    with a:
        st.markdown("### Receitas e despesas")
        ch = alt.Chart(long).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("mes:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
            xOffset="tipo:N", y=alt.Y("valor:Q", title=None),
            color=alt.Color("tipo:N", scale=alt.Scale(domain=["Receitas", "Despesas"], range=[OLIVA, TERRA]), title=None))
        st.altair_chart(estilo(ch), width="stretch")
    with b:
        st.markdown("### Suas metas")
        for m in st.session_state.metas:
            f = m["guardado"] / m["valor"]
            st.markdown(f'<div style="margin-bottom:.9rem"><b>{m["nome"]}</b> <span style="float:right" class="serif">{pct(f, 0)}</span>'
                        f'{barra(f)}<span class="lbl">{brl(m["guardado"])} de {brl(m["valor"])}</span></div>',
                        unsafe_allow_html=True)
        with st.expander("Adicionar meta"):
            with st.form("nova_meta", clear_on_submit=True):
                n = st.text_input("Nome")
                v = st.number_input("Valor desejado (R$)", min_value=1.0, value=5000.0, step=500.0)
                g = st.number_input("Já guardado (R$)", min_value=0.0, value=0.0, step=100.0)
                p = st.number_input("Prazo (meses)", min_value=1, value=12)
                ap = st.number_input("Aporte mensal atual (R$)", min_value=0.0, value=0.0, step=50.0)
                if st.form_submit_button("Salvar meta") and n:
                    st.session_state.metas.append({"nome": n, "valor": v, "guardado": g, "prazo": int(p), "aporte": ap})
                    st.rerun()
    proj = motor.projetar_sobra(df, 6)
    futuro = SALDO_ATUAL + float(proj["previsao"].sum())
    st.markdown(f"""<div class="card" style="background:{OLIVA};color:#FBF7EE;margin-top:.5rem">
    <div style="opacity:.85">Saldo estimado daqui a 6 meses</div><div class="big" style="color:#FBF7EE">{brl(futuro)}</div>
    <div style="opacity:.9;color:#FBF7EE;font-size:.82rem">Projeção pela tendência da sua sobra mensal (regressão linear, R² = {proj['r2']:.2f}).
    Com R² baixo, a sobra é praticamente estável e a projeção equivale à média.</div></div>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ lançamentos
def pagina_lancamentos():
    df = st.session_state.df
    st.markdown("# Lançamentos")
    st.caption("Registre o que entrou e o que saiu. Tudo que aparece nas outras telas é calculado a partir daqui.")
    subs = (df[df["tipo"] == "despesa"][["categoria", "subcategoria"]].drop_duplicates()
            .sort_values(["categoria", "subcategoria"]))
    with st.form("novo_lanc", clear_on_submit=True):
        c = st.columns([1, 1, 2, 1])
        data = c[0].date_input("Data", value=date.today(), format="DD/MM/YYYY")
        tipo = c[1].selectbox("Tipo", ["despesa", "receita"])
        opcoes = [f"{a} › {b}" for a, b in zip(subs["categoria"], subs["subcategoria"])]
        cat = c[2].selectbox("Categoria (só para despesas)", opcoes)
        valor = c[3].number_input("Valor (R$)", min_value=0.01, value=50.0, step=10.0)
        if st.form_submit_button("Registrar"):
            if tipo == "receita":
                linha = (pd.Timestamp(data), "receita", "Salário", "Salário", valor, False)
            else:
                ct, sb = cat.split(" › ")
                linha = (pd.Timestamp(data), "despesa", ct, sb, valor, sb in ESSENCIAIS)
            novo = pd.concat([df, pd.DataFrame([linha], columns=df.columns)], ignore_index=True)
            novo.to_csv(CSV, index=False)
            st.session_state.df = novo
            st.success("Lançamento registrado.")
            st.rerun()
    st.markdown("### Últimos lançamentos")
    ver = df.sort_values("data", ascending=False).head(25).copy()
    ver["data"] = ver["data"].dt.strftime("%d/%m/%Y")
    ver["valor"] = ver["valor"].map(brl)
    st.dataframe(ver[["data", "tipo", "categoria", "subcategoria", "valor"]], hide_index=True, width="stretch")
    if st.button("Restaurar dados de demonstração"):
        gerar().to_csv(CSV, index=False)
        st.session_state.df = carregar()
        st.rerun()


# -------------------------------------------------------------------- simulação
GRUPOS_TXT = {"aporte": "Guardar mais por mês", "despesas": "Gastar menos",
              "prazo": "Esperar um pouco mais", "aplicação": "Fazer o dinheiro render"}


def pagina_simulacao():
    df, r, grupos, flex = contexto()
    ss = st.session_state
    st.markdown("# Simulação")
    st.caption("Mude os parâmetros e veja o que acontece com a meta. O sistema também sugere caminhos.")
    esq, dir_ = st.columns([1, 1.7], gap="large")
    with esq:
        nomes = [m["nome"] for m in ss.metas]
        meta = ss.metas[nomes.index(st.selectbox("Meta", nomes, index=min(1, len(nomes) - 1)))]
        k = meta["nome"]
        valor = st.number_input("Valor desejado (R$)", min_value=1.0, value=meta["valor"], step=500.0, key=f"v{k}")
        guardado = st.number_input("Já guardado (R$)", min_value=0.0, value=meta["guardado"], step=100.0, key=f"g{k}")
        prazo = st.number_input("Prazo (meses)", min_value=1, value=int(meta["prazo"]), key=f"p{k}")
        aporte = st.number_input("Aporte mensal atual (R$)", min_value=0.0, value=meta["aporte"], step=50.0, key=f"a{k}")
        st.markdown("**E se eu mudasse...**")
        aumento = st.slider("Aumentar o aporte em (R$)", 0, 1500, 0, 25, key=f"au{k}")
        corte = st.slider("Reduzir despesas flexíveis em (%)", 0, 40, 0, key=f"co{k}")
        aplic = st.selectbox("Onde o dinheiro fica", ["parado (sem rendimento)"] + list(ss.taxas), key=f"ap{k}")
        with st.expander("Parâmetros do modelo"):
            for nome in list(ss.taxas):
                ss.taxas[nome] = st.number_input(f"Rendimento {nome} (% a.m.)", 0.0, 5.0, ss.taxas[nome], 0.05)
            pe = st.slider("Peso do esforço (o resto vai para o atraso)", 0.0, 1.0, 0.7, 0.05)
            st.caption("Taxas ilustrativas, sem imposto nem inflação. Consulte as taxas reais antes de aplicar.")

    cen = motor.Cenario(meta=valor, guardado=guardado, prazo=int(prazo), aporte_atual=aporte,
                        receitas=r["receitas"], sobra=r["sobra"], flexivel_total=flex,
                        taxas={n: t / 100 for n, t in ss.taxas.items()})
    atual = motor.avaliar(cen)
    taxa_alt = 0.0 if aplic.startswith("parado") else ss.taxas[aplic] / 100
    aporte_alt = aporte + aumento + corte / 100 * flex
    saldo_alt = motor.valor_futuro(guardado, aporte_alt, int(prazo), taxa_alt)
    cob_alt = saldo_alt / valor
    ver_alt = motor.classificar(cob_alt)

    with dir_:
        a, b = st.columns(2)
        a.markdown(f'<div class="card"><div class="lbl">Como está hoje</div><div class="big">{brl(atual["saldo_projetado"])}</div>'
                   f'<div class="lbl">em {int(prazo)} meses, {pct(atual["cobertura"], 0)} da meta</div>{barra(atual["cobertura"], TERRA)}'
                   f'<div class="{classe(atual["veredito"])}">Meta {atual["veredito"]}</div></div>', unsafe_allow_html=True)
        b.markdown(f'<div class="card" style="border-color:{OLIVA}"><div class="lbl">Se eu mudasse</div><div class="big">{brl(saldo_alt)}</div>'
                   f'<div class="lbl">aporte de {brl(aporte_alt)}, {pct(cob_alt, 0)} da meta</div>{barra(cob_alt, OLIVA)}'
                   f'<div class="{classe(ver_alt)}">Meta {ver_alt}</div></div>', unsafe_allow_html=True)
        if aporte_alt > r["sobra"]:
            st.warning(f"Esse aporte ({brl(aporte_alt)}) passa da sua sobra mensal ({brl(r['sobra'])}).")
        n = int(prazo)
        meses = list(range(n + 1))
        linhas = pd.DataFrame({"mês": meses,
                               "Hoje": [motor.valor_futuro(guardado, aporte, m) for m in meses],
                               "Se eu mudasse": [motor.valor_futuro(guardado, aporte_alt, m, taxa_alt) for m in meses]}
                              ).melt("mês", var_name="cenário", value_name="saldo")
        base = alt.Chart(linhas).mark_line(strokeWidth=3).encode(
            x=alt.X("mês:Q", title="meses a partir de agora"), y=alt.Y("saldo:Q", title=None),
            color=alt.Color("cenário:N", scale=alt.Scale(domain=["Hoje", "Se eu mudasse"], range=[TERRA, OLIVA]), title=None))
        regra = alt.Chart(pd.DataFrame({"y": [valor]})).mark_rule(strokeDash=[5, 4], color=TINTA).encode(y="y:Q")
        st.altair_chart(estilo(base + regra, 250), width="stretch")
        st.caption("A linha tracejada é o valor da meta.")

    rec = motor.recomendar(cen, (pe, 1 - pe))
    st.markdown("## O que o FinPlan sugere")
    if atual["veredito"] != "inviável":
        st.success(rec["texto"])
    else:
        st.markdown(f"**{rec['texto']}**")
    por_tipo = {}
    for alt_ in rec["alternativas"]:
        por_tipo.setdefault(alt_.tipo, []).append(alt_)
    melhor = rec.get("melhor")
    ordem = sorted(por_tipo, key=lambda t: min((not x.viavel, x.nota) for x in por_tipo[t]))
    for t in ordem:
        st.markdown(f'<div class="grp">{GRUPOS_TXT[t]}</div>', unsafe_allow_html=True)
        for x in por_tipo[t]:
            tag = '<span class="rec">recomendada</span>' if x is melhor else ""
            cor = "ok" if x.viavel else "bad"
            st.markdown(f'<div class="card" style="margin-bottom:.4rem">{x.descricao}{tag}<br>'
                        f'<span class="nota">esforço extra: {pct(x.esforco, 1)} da renda · atraso: {x.atraso} meses · '
                        f'<span class="{cor}">{"cabe" if x.viavel else "não cabe"}</span> — {x.motivo}</span></div>',
                        unsafe_allow_html=True)
    if flex:
        sug = grupos[(grupos["grupo"] == "variável")].sort_values("media", ascending=False)
        if len(sug):
            itens = ", ".join(f"{s} ({brl(m)})" for s, m in zip(sug["subcategoria"], sug["media"]))
            st.markdown(f'<div class="nota" style="margin-top:.6rem">Se for cortar, comece pelo que mais varia mês a mês: {itens}.</div>',
                        unsafe_allow_html=True)
    if st.button("Salvar esta simulação"):
        ss.simulacoes.append({"Meta": k, "Cenário": f"aporte {brl(aporte_alt)}, corte {corte}%, {aplic}",
                              "Cobertura": pct(cob_alt, 0), "Resultado": ver_alt})
        st.success("Simulação salva em Relatórios.")


# -------------------------------------------------------------------- relatórios
def pagina_relatorios():
    df, r, grupos, flex = contexto()
    st.markdown("# Relatórios")
    per = st.selectbox("Período", [3, 6, 12, 24], index=1, format_func=lambda n: f"Últimos {n} meses")
    s = motor.serie_mensal(df).tail(per)
    s["taxa"] = s["sobra"] / s["receita"]
    s["saldo"] = SALDO_ATUAL - s["sobra"][::-1].cumsum()[::-1].shift(-1).fillna(0)
    s["rotulo"] = [rotulo(p) for p in s.index]
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("### Histórico mensal")
        long = s.reset_index(drop=True).melt(id_vars="rotulo", value_vars=["receita", "despesa"], var_name="tipo", value_name="valor")
        ch = alt.Chart(long).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("rotulo:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)), xOffset="tipo:N",
            y=alt.Y("valor:Q", title=None),
            color=alt.Color("tipo:N", scale=alt.Scale(domain=["receita", "despesa"], range=[OLIVA, TERRA]), title=None))
        st.altair_chart(estilo(ch), width="stretch")
    with b:
        st.markdown("### Para onde foi o dinheiro")
        d = df[df["tipo"] == "despesa"].copy()
        d["mes"] = d["data"].dt.to_period("M")
        d = d[d["mes"].isin(s.index)].groupby("categoria")["valor"].sum().div(per).sort_values(ascending=False)
        tot = d.sum()
        for cat, v in d.items():
            st.markdown(f'<div style="margin-bottom:.5rem"><b>{cat}</b><span style="float:right">{brl(v)} por mês</span>'
                        f'{barra(v / d.max(), OCRE)}</div>', unsafe_allow_html=True)
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("### Saldo e taxa de poupança")
        ch1 = alt.Chart(s.reset_index(drop=True)).mark_line(strokeWidth=3, color=OLIVA, point=alt.OverlayMarkDef(color=OLIVA)).encode(
            x=alt.X("rotulo:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("saldo:Q", title="saldo (R$)"))
        ch2 = alt.Chart(s.reset_index(drop=True)).mark_line(strokeWidth=2, color=TERRA, strokeDash=[5, 3]).encode(
            x=alt.X("rotulo:N", sort=None), y=alt.Y("taxa:Q", title="taxa de poupança", axis=alt.Axis(format="%")))
        st.altair_chart(estilo(alt.layer(ch1, ch2).resolve_scale(y="independent"), 240), width="stretch")
        st.caption("Verde: saldo. Tracejado terracota: taxa de poupança.")
    with b:
        st.markdown("### Grupos de despesas")
        g = grupos.copy()
        g["média mensal"] = g["media"].map(brl)
        g["variação"] = g["cv"].map(lambda x: pct(x, 0))
        g = g.sort_values(["grupo", "media"], ascending=[True, False])
        st.dataframe(g[["subcategoria", "grupo", "média mensal", "variação"]].rename(columns={"subcategoria": "item", "grupo": "grupo"}),
                     hide_index=True, width="stretch", height=260)
    st.markdown("### Metas")
    cols = st.columns(len(st.session_state.metas))
    for col, m in zip(cols, st.session_state.metas):
        f = m["guardado"] / m["valor"]
        col.markdown(f'<div class="card"><b>{m["nome"]}</b><span style="float:right" class="serif">{pct(f, 0)}</span>{barra(f)}'
                     f'<span class="lbl">faltam {brl(m["valor"] - m["guardado"])}</span></div>', unsafe_allow_html=True)
    st.markdown("### Simulações salvas")
    if st.session_state.simulacoes:
        st.dataframe(pd.DataFrame(st.session_state.simulacoes), hide_index=True, width="stretch")
    else:
        st.caption("Nenhuma simulação salva ainda. Salve uma na tela Simulação.")
    exp = s[["rotulo", "receita", "despesa", "sobra", "taxa", "saldo"]].rename(columns={"rotulo": "mes"})
    st.download_button("Exportar período (CSV)", exp.to_csv(index=False).encode("utf-8"), "finplan_relatorio.csv", "text/csv")


# --------------------------------------------------------------------- principal
estado()
if not st.session_state.logado:
    tela_login()
else:
    with st.sidebar:
        st.markdown('<div class="serif" style="font-size:1.6rem;color:#C0603A">FinPlan</div>', unsafe_allow_html=True)
        pagina = st.radio("Menu", ["Visão geral", "Lançamentos", "Simulação", "Relatórios"], label_visibility="collapsed")
        st.write("")
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()
    {"Visão geral": pagina_geral, "Lançamentos": pagina_lancamentos,
     "Simulação": pagina_simulacao, "Relatórios": pagina_relatorios}[pagina]()
