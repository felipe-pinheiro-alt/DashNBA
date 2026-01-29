import time
import pandas as pd
import streamlit as st
import plotly.express as px
from nba_api.stats.endpoints import LeagueDashTeamStats

# ===================== PAGE CONFIG =====================
st.set_page_config(
    page_title="NBA Analytics Hub",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===================== STYLE (minimal + stable) =====================
st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

  .stApp{
    font-family: 'Inter', sans-serif;
    background:
      radial-gradient(1100px 600px at 15% 10%, rgba(102,126,234,.18), transparent 60%),
      radial-gradient(900px 520px at 80% 25%, rgba(118,75,162,.16), transparent 55%),
      linear-gradient(135deg, #060817 0%, #0b1020 60%, #060817 100%);
  }

  .block-container { padding-top: 2rem; padding-bottom: 2.5rem; }

  .main-title{
    font-size: 3.1rem;
    font-weight: 800;
    text-align: center;
    margin: 0.2rem 0 0.25rem 0;
    letter-spacing: 0.6px;
    background: linear-gradient(135deg, #93c5fd 0%, #667eea 45%, #a78bfa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 28px rgba(102,126,234,.24);
  }

  .subtitle{
    text-align: center;
    color: rgba(229,231,235,.78);
    font-size: 1.05rem;
    margin-bottom: 1.2rem;
    font-weight: 400;
  }

  .section-header{
    font-size: 1.6rem;
    font-weight: 750;
    color: rgba(255,255,255,.92);
    margin: 1.5rem 0 0.8rem 0;
    padding-left: 0.9rem;
    border-left: 4px solid rgba(102,126,234,.85);
  }

  /* Metric cards */
  div[data-testid="metric-container"]{
    background: linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.025) 100%);
    border: 1px solid rgba(255,255,255,0.12);
    padding: 1.1rem 1.2rem;
    border-radius: 16px;
    box-shadow: 0 10px 26px rgba(0,0,0,.25);
  }

  div[data-testid="metric-container"] label{
    color: rgba(229,231,235,.75) !important;
    font-weight: 650 !important;
    text-transform: uppercase;
    letter-spacing: .08em;
    font-size: .78rem !important;
  }

  div[data-testid="metric-container"] [data-testid="stMetricValue"]{
    font-size: 2.0rem !important;
    font-weight: 850 !important;
    color: rgba(255,255,255,.95);
  }

  /* Dataframe */
  div[data-testid="stDataFrame"]{
    background: rgba(255,255,255,0.03);
    border-radius: 16px;
    padding: .25rem;
    border: 1px solid rgba(255,255,255,0.12);
    box-shadow: 0 10px 26px rgba(0,0,0,.18);
  }
</style>
""",
    unsafe_allow_html=True,
)

# ===================== CONSTANTS =====================
SEASONS = [
    "2014-15", "2015-16", "2016-17", "2017-18", "2018-19",
    "2019-20", "2020-21", "2021-22", "2022-23", "2023-24"
]

CHAMPIONS_DATA = {
    "2014-15": "Golden State Warriors",
    "2015-16": "Cleveland Cavaliers",
    "2016-17": "Golden State Warriors",
    "2017-18": "Golden State Warriors",
    "2018-19": "Toronto Raptors",
    "2019-20": "Los Angeles Lakers",
    "2020-21": "Milwaukee Bucks",
    "2021-22": "Golden State Warriors",
    "2022-23": "Denver Nuggets",
    "2023-24": "Boston Celtics"
}

ACCENT = "#667eea"
ACCENT_2 = "#a78bfa"

# ===================== DATA (cached, no disk writes) =====================
@st.cache_data(ttl=60 * 60 * 24 * 7, show_spinner=False)
def fetch_team_stats_for_season(season: str) -> pd.DataFrame:
    stats = LeagueDashTeamStats(season=season, per_mode_detailed="PerGame")
    df = stats.get_data_frames()[0].copy()
    df["SEASON"] = season
    return df

@st.cache_data(ttl=60 * 60 * 24 * 7, show_spinner="Buscando dados da NBA (pode demorar na 1ª vez)...")
def load_dataset() -> pd.DataFrame:
    frames = []
    for s in SEASONS:
        df_s = fetch_team_stats_for_season(s)
        frames.append(df_s)
        time.sleep(0.35)  # gentle pacing

    df = pd.concat(frames, ignore_index=True)

    keep = ["SEASON", "TEAM_NAME", "GP", "W", "L", "FG3M", "FG3A", "FG3_PCT", "PTS"]
    df = df[keep].copy()

    # Normalize FG3_PCT to 0-100 if needed
    if df["FG3_PCT"].max() <= 1:
        df["FG3_PCT"] = df["FG3_PCT"] * 100

    # Derived metrics
    df["THREES_PER_GAME"] = df["FG3M"]
    df["THREES_ATT_PER_GAME"] = df["FG3A"]
    df["POINTS_FROM_3"] = df["FG3M"] * 3
    df["PERCENT_POINTS_3"] = (df["POINTS_FROM_3"] / df["PTS"]) * 100

    champs_df = pd.DataFrame(list(CHAMPIONS_DATA.items()), columns=["SEASON", "CHAMPION_TEAM"])
    df = df.merge(champs_df, on="SEASON", how="left")
    df["IS_CHAMPION"] = df["TEAM_NAME"] == df["CHAMPION_TEAM"]

    return df

# ===================== UI HELPERS =====================
def render_metrics(df_filtered: pd.DataFrame):
    c1, c2, c3, c4 = st.columns(4)

    avg_att = df_filtered["THREES_ATT_PER_GAME"].mean()
    avg_pct = df_filtered["FG3_PCT"].mean()

    champ_row = df_filtered[df_filtered["IS_CHAMPION"]].head(1)

    with c1:
        st.metric("Tentativas 3PT/Jogo", f"{avg_att:.1f}", "Liga")

    with c2:
        st.metric("3PT% médio", f"{avg_pct:.1f}%", "Liga")

    with c3:
        if not champ_row.empty:
            champ_pct = float(champ_row.iloc[0]["FG3_PCT"])
            st.metric("Campeão — 3PT%", f"{champ_pct:.1f}%", f"{(champ_pct - avg_pct):+.1f}%")
        else:
            st.metric("Campeão — 3PT%", "N/A")

    with c4:
        if not champ_row.empty:
            p3 = float(champ_row.iloc[0]["PERCENT_POINTS_3"])
            st.metric("% pontos do 3PT", f"{p3:.1f}%", "Campeão")
        else:
            st.metric("% pontos do 3PT", "N/A")

def plot_top_bar(df_filtered: pd.DataFrame):
    top = (
        df_filtered.nlargest(10, "THREES_PER_GAME")
        .sort_values("THREES_PER_GAME")
        .copy()
    )

    fig = px.bar(
        top,
        x="THREES_PER_GAME",
        y="TEAM_NAME",
        orientation="h",
        text="THREES_PER_GAME",
        color="IS_CHAMPION",
        color_discrete_map={True: ACCENT_2, False: ACCENT},
        title="Top 10 — 3PT por jogo",
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
    fig.update_layout(
        template="plotly_dark",
        height=440,
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis_title="3PT/Jogo",
        yaxis_title="",
        legend_title_text="Campeão",
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_scatter(df_filtered: pd.DataFrame):
    fig = px.scatter(
        df_filtered,
        x="THREES_ATT_PER_GAME",
        y="FG3_PCT",
        size="W",
        color="IS_CHAMPION",
        hover_name="TEAM_NAME",
        color_discrete_map={True: ACCENT_2, False: ACCENT},
        title="Volume vs Eficiência — Tentativas 3PT/Jogo x 3PT%",
    )
    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis_title="Tentativas de 3PT/Jogo",
        yaxis_title="3PT (%)",
        legend_title_text="Campeão",
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_evolution(df_all: pd.DataFrame):
    league = df_all.groupby("SEASON", as_index=False)["THREES_ATT_PER_GAME"].mean()
    league["Série"] = "Liga (média)"

    champs = df_all[df_all["IS_CHAMPION"]][["SEASON", "THREES_ATT_PER_GAME"]].copy()
    champs["Série"] = "Campeão"

    df_plot = pd.concat([league, champs], ignore_index=True)

    fig = px.line(
        df_plot,
        x="SEASON",
        y="THREES_ATT_PER_GAME",
        color="Série",
        markers=True,
        title="Evolução — Tentativas de 3 por jogo (Liga vs Campeão)",
        color_discrete_map={"Liga (média)": ACCENT, "Campeão": ACCENT_2},
    )
    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis_title="Temporada",
        yaxis_title="Tentativas de 3PT/Jogo",
    )
    st.plotly_chart(fig, use_container_width=True)

# ===================== APP =====================
def main():
    st.markdown('<div class="main-title">NBA ANALYTICS HUB</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Revolução dos 3 pontos (2014–2024) • Community Cloud ready</div>', unsafe_allow_html=True)

    # Sidebar controls
    st.sidebar.markdown("## ⚙️ Filtros")
    st.sidebar.markdown("---")

    if st.sidebar.button("🔄 Atualizar dados (limpar cache)"):
        st.cache_data.clear()
        st.rerun()

    df = load_dataset()

    with st.sidebar.form("filters"):
        selected_season = st.selectbox(
            "📅 Temporada",
            options=sorted(df["SEASON"].unique(), reverse=True),
            index=0
        )

        df_season = df[df["SEASON"] == selected_season].copy()
        teams = sorted(df_season["TEAM_NAME"].unique())

        selected_teams = st.multiselect("🏆 Times", options=teams, default=teams)
        min_fg3_pct = st.slider("🎯 3PT% mínimo", 0, 100, 0, 1)

        apply = st.form_submit_button("Aplicar")

    df_filtered = df_season[df_season["TEAM_NAME"].isin(selected_teams)].copy()
    df_filtered = df_filtered[df_filtered["FG3_PCT"] >= min_fg3_pct].copy()

    tab1, tab2, tab3, tab4 = st.tabs(["Visão geral", "Histórico", "Tabela", "Sobre"])

    with tab1:
        st.markdown('<div class="section-header">📈 Métricas da temporada</div>', unsafe_allow_html=True)
        render_metrics(df_filtered)

        st.markdown('<div class="section-header">🎯 Top 3PT/Jogo</div>', unsafe_allow_html=True)
        plot_top_bar(df_filtered)

        st.markdown('<div class="section-header">🧭 Volume x eficiência</div>', unsafe_allow_html=True)
        plot_scatter(df_filtered)

    with tab2:
        st.markdown('<div class="section-header">📊 Evolução histórica</div>', unsafe_allow_html=True)
        plot_evolution(df)

    with tab3:
        st.markdown('<div class="section-header">📋 Dados detalhados</div>', unsafe_allow_html=True)

        display_cols = [
            "TEAM_NAME", "W", "L",
            "THREES_PER_GAME", "THREES_ATT_PER_GAME",
            "FG3_PCT", "PERCENT_POINTS_3", "IS_CHAMPION"
        ]
        df_display = df_filtered[display_cols].copy().rename(columns={
            "TEAM_NAME": "Time",
            "W": "Vitórias",
            "L": "Derrotas",
            "THREES_PER_GAME": "3PT/Jogo",
            "THREES_ATT_PER_GAME": "Tentativas 3PT/Jogo",
            "FG3_PCT": "3PT %",
            "PERCENT_POINTS_3": "% Pontos do 3PT",
            "IS_CHAMPION": "Campeão",
        })

        st.dataframe(df_display, use_container_width=True, height=460)

        csv = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Baixar CSV da temporada",
            data=csv,
            file_name=f"nba_stats_{selected_season}.csv",
            mime="text/csv",
        )

    with tab4:
        st.markdown('<div class="section-header">ℹ️ Sobre</div>', unsafe_allow_html=True)
        st.write(
            "Este app usa nba_api (LeagueDashTeamStats) em modo PerGame e destaca o campeão por temporada. "
            "Os dados são cacheados para ficar rápido no Community Cloud."
        )

if __name__ == "__main__":
    main()
