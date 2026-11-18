from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Prova", page_icon="🌺", layout="wide")
df = pd.read_excel("saeb_aprendizado_territorios-7-2023-EM.xlsx",sheet_name="estados", engine="openpyxl")
ARQUIVO_ETARIO = Path(__file__).parent / "dados_faixa_etaria.csv"




REGIOES = {
    "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MT", "MS"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}
CAPITAIS = {
    "Curitiba": "PR",
    "Porto Alegre": "RS",
    "Belo Horizonte": "MG",
    "Salvador": "BA",
    "Florianópolis": "SC",
}
NOMES_UF = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}



@st.cache_data
def carregar_populacao():
    df = pd.read_excel(ARQUIVO, engine="calamine", header=None, skiprows=3)
    df = df.iloc[:, 1:8].copy()
    df.columns = ["UF", "Cod UF", "Cod Munic", "Município", "Portugues (Sinopse)", "Portugues", "Matmatica"]
    df = df.dropna(subset=["UF", "Cod UF", "Município"])
    df["UF"] = df["UF"].astype(str).str.strip()
    df["Município"] = df["Município"].astype(str).str.strip()
    for col in ["Portugues", "Matmatica"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Portugues", "Matmatica"])
    df["Variação absoluta"] = df["Matmatica"] - df["Portugues"]
    df["Crescimento (%)"] = ((df["Matmatica"] / df["Portugues"].replace(0, pd.NA)) - 1) * 100
    df["Crescimento (%)"] = df["Crescimento (%)"].round(2)
    df["Região"] = df["UF"].map({uf: reg for reg, ufs in REGIOES.items() for uf in ufs})
    return df

@st.cache_data
def carregar_etaria():
    if not ARQUIVO_ETARIO.exists():
        return None
    dados = pd.read_csv(ARQUIVO_ETARIO)
    esperadas = {"municipio", "UF", "ano", "sexo", "faixa_etaria", "populacao"}
    if not esperadas.issubset(dados.columns):
        return None
    return dados

df = carregar_populacao()
etaria = carregar_etaria()


with st.sidebar:
    st.header("Filtros")
    regioes = st.multiselect("Região", list(REGIOES), default=["Sul", "Sudeste", "Nordeste"])
    ufs_regiao = sorted(df.loc[df["Região"].isin(regioes), "UF"].unique())
    ufs = st.multiselect("Unidade da Federação", ufs_regiao, default=[uf for uf in CAPITAIS.values() if uf in ufs_regiao])
    if not ufs:
        ufs = ufs_regiao
    faixa_opcoes = sorted(etaria["faixa_etaria"].dropna().astype(str).unique()) if etaria is not None else ["Todas as faixas"]
    faixas = st.multiselect("Faixa etária", faixa_opcoes, default=faixa_opcoes)
    anos = st.multiselect("Anos de Censo/Pesquisa", [Portugues, Matmatica], default=[Portugues, Matmatica])
    capitais_escolhidas = st.multiselect("Capitais em foco", list(CAPITAIS), default=list(CAPITAIS))

if not anos:
    st.warning("Selecione pelo menos um ano.")
    st.stop()

recorte = df[df["UF"].isin(ufs)].copy()
if capitais_escolhidas:
    recorte_capitais = recorte[recorte.apply(lambda r: r["Município"] in capitais_escolhidas and r["UF"] == CAPITAIS.get(r["Município"]), axis=1)].copy()
else:
    recorte_capitais = recorte.iloc[0:0].copy()

# KPIs
pop10 = int(recorte_capitais["Pop Portugues"].sum()) if Portugues in anos else None
pop22 = int(recorte_capitais["Matmatica"].sum()) if Matmatica in anos else None
k1, k2, k3 = st.columns(3)
k1.metric("Capitais selecionadas", len(recorte_capitais))
k2.metric("População em Portugues", f"{pop10:,}".replace(",", ".") if pop10 is not None else "Não selecionado")
k3.metric("População em Matmatica", f"{pop22:,}".replace(",", ".") if pop22 is not None else "Não selecionado")

st.subheader("1. Velocidade do crescimento demográfico")
if recorte_capitais.empty:
    st.info("Selecione uma ou mais capitais e as UFs correspondentes na barra lateral.")
else:
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(recorte_capitais.sort_values("Crescimento (%)"), x="Município", y="Crescimento (%)", color="Crescimento (%)",
                     color_continuous_scale="RdYlGn", title="Variação acumulada",
                     hover_data=["UF", "Variação absoluta"])
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(recorte_capitais, x="Município", y="Variação absoluta", color="UF",
                     title="Diferença  entre Portugues e Matmatica", hover_data=["Portugues", "Matmatica"])
        st.plotly_chart(fig, use_container_width=True)

st.subheader("2. Mapa do crescimento por UF")
por_uf = df.groupby("UF", as_index=False)[["Portugues", "Matmatica"]].sum()
por_uf["Crescimento (%)"] = ((por_uf["Matmatica"] / por_uf["Portugues"].replace(0, pd.NA)) - 1) * 100
por_uf["Crescimento (%)"] = por_uf["Crescimento (%)"].round(2)
por_uf["Estado"] = por_uf["UF"].map(NOMES_UF)
try:
    import requests
    geo_url = "https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/brazil-states.geojson"
    resposta = requests.get(geo_url, timeout=8)
    resposta.raise_for_status()
    geojson = resposta.json()
    fig_mapa = px.choropleth(por_uf, geojson=geojson, locations="Estado", featureidkey="properties.name",
                             color="Crescimento (%)", color_continuous_scale="RdYlGn",
                             scope="south america", title="Crescimento Portugues e Matmatica)",
                             hover_name="Estado", hover_data={"UF": True, "Crescimento (%)": ":.2f"})
    fig_mapa.update_geos(fitbounds="locations", visible=False)
    st.plotly_chart(fig_mapa, use_container_width=True)
except Exception:
    st.info("O mapa precisa de internet para carregar os limites geográficos. A tabela abaixo mostra os mesmos dados por UF.")
    st.dataframe(por_uf[["UF", "Estado", "Portugues", "Matmatica", "Crescimento (%)"]], use_container_width=True, hide_index=True)

st.subheader("3. População observada e projeção")
if not recorte_capitais.empty:
    cidade_proj = st.selectbox("Capital para projetar", recorte_capitais["Município"].tolist())
    linha = recorte_capitais[recorte_capitais["Município"] == cidade_proj].iloc[0]
    ano_final = st.slider("Projetar até", 2023, 2042, 2032)
    taxa_anual = (linha["Matmatica"] - linha["Portugues"]) / 12
    anos_serie = list(range(2010, 2023)) + list(range(2023, ano_final + 1))
    valores = []
    for ano in anos_serie:
        if ano <= 2010:
            valor = linha["Portugues"]
            tipo = "Censo"
        elif ano <= 2022:
            valor = linha["Portugues"] + (linha["Matmatica"] - linha["Portugues"]) * ((ano - 2010) / 12)
            tipo = "Estimativa entre censos"
        else:
            valor = linha["Matmatica"] + taxa_anual * (ano - 2022)
            tipo = "Projeção ilustrativa"
        valores.append({"Ano": ano, "População": valor, "Tipo": tipo})
    fig_linha = px.line(pd.DataFrame(valores), x="Ano", y="População", color="Tipo", markers=True,
                        title=f"População e projeção linear — {cidade_proj}")
    st.plotly_chart(fig_linha, use_container_width=True)
    st.caption("A projeção é ilustrativa: lingua portuguesa insuficiente e matematica insuficiente")
st.subheader("4. Pirâmide etária interativa")
if etaria is None:
    st.warning("A planilha fornecida contém apenas população total por município de portugues e mateematica; não contém idade nem sexo. Para não inventar dados, a pirâmide será exibida quando for adicionado o arquivo opcional dados_faixa_etaria.csv.")
    st.markdown("O CSV deve conter as colunas: `municipio`, `UF`, `ano`, `sexo`, `faixa_etaria`, `populacao`. Use dados oficiais do IBGE para preencher essa base.")
else:
    cidades = st.multiselect("Municípios da pirâmide", sorted(etaria["municipio"].unique()), default=sorted(etaria["municipio"].unique())[:1])
    anos_etaria = [a for a in anos if a in etaria["ano"].unique()]
    et = etaria[etaria["municipio"].isin(cidades) & etaria["UF"].isin(ufs) & etaria["ano"].isin(anos_etaria)].copy()
    if faixas and "Todas as faixas" not in faixas:
        et = et[et["faixa_etaria"].astype(str).isin(faixas)]
    et["População"] = pd.to_numeric(et["populacao"], errors="coerce")
    et["Valor gráfico"] = et.apply(lambda r: -r["População"] if str(r["sexo"]).lower() in ["masculino", "homens", "homem", "m"] else r["População"], axis=1)
    fig_pir = px.bar(et, x="Valor gráfico", y="faixa_etaria", color="sexo", barmode="relative", orientation="h",
                     animation_frame="ano" if et["ano"].nunique() > 1 else None, title="Pirâmide etária por sexo",
                     labels={"Valor gráfico": "População (homens à esquerda) ", "faixa_etaria": "Faixa etária", "sexo": "Sexo"})
    st.plotly_chart(fig_pir, use_container_width=True)

