import streamlit as st
import pandas as pd
import plotly.express as px


st.set_page_config(layout="wide")

# =========================
# 🎨 ESTILO GLOBAL
# =========================
st.markdown("""
<style>
    body {
        background-color: #0f172a;
    }

    .stMetric {
        background-color: #111827;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }

    section[data-testid="stSidebar"] {
        background-color: #020617;
    }

    h1, h2, h3 {
        color: #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# TITULO
# =========================
st.title("📊 Monitoramento Corporativo de Backups")
st.caption("Visão executiva - Data Protector")
st.success("🟢 Sistema ativo e monitorando backups em tempo real")
if st.button("🔄 Atualizar dados"):
    st.cache_data.clear()

# =========================
# LOAD
# =========================
@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(
        "C:/DEV/Dashboard/DADOS/backup.csv",
        sep="\t",
        skiprows=6,
        header=None
    )

    df.columns = [
        "Tipo", "Backup", "Status", "Modo",
        "Inicio", "ID1", "Fim", "ID2",
        "Duracao", "Tempo", "GB",
        "C1","C2","C3","C4","C5","C6","C7","C8","C9",
        "Percentual", "Usuario", "Data"
    ]

    return df

df = carregar_dados()

# ✅ CONVERTE INICIO
df["Inicio"] = pd.to_datetime(df["Inicio"], dayfirst=True, errors="coerce")

# ✅ CRIA DIA
df["Dia"] = df["Inicio"].dt.date

# =========================
# TRATAMENTO
# =========================
df["Inicio"] = pd.to_datetime(df["Inicio"], errors="coerce")

# ✅ CONVERTE TEMPO (COLOQUE AQUI)
df["Tempo"] = pd.to_timedelta(df["Tempo"].astype(str) + ":00", errors="coerce")

# (coluna - tempo minutos)
df["Tempo_Minutos"] = df["Tempo"].dt.total_seconds().fillna(0) / 60

def formatar_tempo(td):
    if pd.isna(td):
        return "-"
    total_segundos = int(td.total_seconds())
    horas = total_segundos // 3600
    minutos = (total_segundos % 3600) // 60
    segundos = total_segundos % 60
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

df["Tempo_Formatado"] = df["Tempo"].apply(formatar_tempo)

df["GB"] = df["GB"].astype(str).str.replace(",", ".")
df["GB"] = df["GB"].str.replace(" GB", "")
df["GB"] = pd.to_numeric(df["GB"], errors="coerce").fillna(0)

def formatar_tamanho(valor):
    if valor >= 1:
        return f"{valor:.1f} GB"
    else:
        return f"{valor * 1024:.0f} MB"

df["Tamanho"] = df["GB"].apply(formatar_tamanho)

def destaque_tamanho(val):
    if "GB" in val and float(val.split()[0]) >= 200:
        return "color: #ef4444; font-weight: bold"
    return ""


def destaque_status(val):
    if val == "❌":
        return "color: #ef4444; font-weight: bold"  # vermelho
    elif val == "✅":
        return "color: #22c55e; font-weight: bold"  # verde
    return ""

def destaque_estado(val):
    if val in ["Processando"]:
        return "color: #1E90FF; font-weight: bold"  # 🔵 azul
    if val in ["Erro"]:
        return "color: #ef4444; font-weight: bold"  # 🔴 vermelho
    elif val in ["Completo/Erros"]:
        return "color: #facc15; font-weight: bold"  # 🟡 amarelo
    elif val in ["Completo"]:
        return "color: #22c55e; font-weight: bold"  # 🟢 verde
    return ""

def destacar_processando(row):
    if row["Estado"] == "Processando":
        return ["background-color: rgba(30,144,255,0.15)"] * len(row)
    return [""] * len(row)


# Padronização de status
df["Status"] = df["Status"].astype(str).str.upper()

df["Status"] = df["Status"].replace({
    "FAILED": "Failed",
    "FAIL": "Failed",
    "COMPLETED": "Completed",
    "SUCCESS": "Completed",
    "COMPLETED/FAILURES": "Completed/Failures" 
})

def definir_estado(row):
    status = str(row["Status"]).upper()
    fim = str(row["Fim"]).strip()

    # 🔄 Ainda rodando
    if fim in ["", "-", "NONE", "NAN"]:
        return "Processando"

    # ✅ Completo
    if status == "COMPLETED":
        return "Completo"

    # ⚠️ Parcial
    if status == "COMPLETED/FAILURES":
        return "Completo/Erros"

    # ❌ Falha real
    if "FAIL" in status:
        return "Erro"

    return "Desconhecido"

df["Status_Descricao"] = df.apply(definir_estado, axis=1)

def definir_icone(row):
    estado = row["Status_Descricao"]

    if estado == "Processando":
        return "🔄"
    elif estado == "Completo":
        return "✅"
    elif estado == "Completo/Erros":
        return "⚠️"
    elif estado == "Erro":
        return "❌"

    return "❓"

df["Status_Icone"] = df.apply(definir_icone, axis=1)

# Turno
def turno_func(hora):
    if pd.isna(hora):
        return "Desconhecido"
    h = hora.hour
    if 6 <= h < 12:
        return "Matinal"
    elif 12 <= h < 18:
        return "Vespertino"
    else:
        return "Noturno"

df["Turno"] = df["Inicio"].apply(turno_func)

# Tipo backup
def tipo_backup(nome):
    nome = str(nome).upper()
    if "DIARIO" in nome:
        return "Diário"
    elif "WEEKLY" in nome:
        return "Semanal"
    elif "MENSAL" in nome:
        return "Mensal"
    else:
        return "Outros"

df["Categoria"] = df["Backup"].apply(tipo_backup)

df["Dia"] = df["Inicio"].dt.date

# =========================
# RISCO
# =========================
def calcular_risco(row):
    risco = 0

    status = str(row.get("Status", "")).upper()

    # 🔴 Falha
    if "FAIL" in status:
        risco += 6

    # 💽 Consumo por nível
    if row["GB"] > 300:
        risco += 6
    elif row["GB"] >= 200:
        risco += 5
    elif row["GB"] >= 100:
        risco += 4
    elif row["GB"] >= 50:
        risco += 2

    # ⚠️ Problema de data
    if pd.isna(row["Inicio"]):
        risco += 4

    return risco

df["Risco"] = df.apply(calcular_risco, axis=1)

top_risco = (
    df.sort_values("Risco", ascending=False)
    .head(10)
    .reset_index(drop=True)
)

# ✅ 1. Calcula risco numérico
df["Risco"] = df.apply(calcular_risco, axis=1)

# ✅ 2. Classifica nível (texto)
def classificar_risco(valor):
    if valor >= 10:
        return "Muito Alto"
    elif valor >= 7:
        return "Alto"
    elif valor >= 5:
        return "Medio"
    elif valor >= 3:
        return "Baixo"
    else:
        return "Muito Baixo"

def classificar_nivel_por_gb(gb):
    if gb >= 200:
        return "Muito Alto"
    elif gb >= 100:
        return "Alto"
    elif gb >= 50:
        return "Medio"
    elif gb >= 10:
        return "Baixo"
    else:
        return "Muito Baixo"

df["Nivel"] = df["GB"].apply(classificar_nivel_por_gb)
df["Nivel"] = pd.Categorical(
    df["Nivel"],
    categories=["Muito Baixo", "Baixo", "Medio", "Alto", "Muito Alto"],
    ordered=True
)

# =========================
# 🎛️ FILTROS
# =========================
with st.sidebar:
   with st.sidebar:
    st.markdown("## 🎛️ Filtros")

    status = st.multiselect(
        "🚦 Status",
        df["Status"].unique(),
        default=df["Status"].unique()
    )

    turno = st.multiselect(
        "🕐 Turno",
        df["Turno"].unique(),
        default=df["Turno"].unique()
    )

    categoria = st.multiselect(
        "💾 Tipo Backup",
        df["Categoria"].unique(),
        default=df["Categoria"].unique()
    )

# Limites
data_min = df["Dia"].dropna().min()
data_max = df["Dia"].dropna().max()

# 🔥 PERÍODO NA SIDEBAR
st.sidebar.subheader("📅 Período")

data_inicio = st.sidebar.date_input("📅Data início", data_min)
data_fim = st.sidebar.date_input("📅Data fim", data_max)

# Converter input para datetime
data_inicio = data_inicio
data_fim = data_fim

# Aplicar filtros
df = df[
    (df["Status"].isin(status)) &
    (df["Turno"].isin(turno)) &
    (df["Categoria"].isin(categoria)) &
    (df["Dia"] >= data_inicio) &
    (df["Dia"] <= data_fim)
]

# =========================
# ABAS
# =========================
aba1, aba2, aba3 = st.tabs(["📊 Gráficos", "📋 Dados", "⏰ Timeline Backups"])

# =========================
# 📊 GRÁFICOS
# =========================
with aba1:

    st.subheader("🚨 Painel de Alertas")

    col1, col2, col3, col4 = st.columns(4)

    falhas = df[df["Status"].isin(["Failed", "Completed/Failures"])]
    alto = df[df["GB"] > 200]
    risco_alto = df[df["Risco"] >= 5]
    total = len(df)
        
    col1.metric("📊 Registros", total)
    col2.metric("❌ Falhas", len(falhas))
    col3.metric("⚠️ Risco Elevado", len(risco_alto))
    col4.metric("💽 Alto Consumo", len(alto))
        
    if len(falhas) >= 3:
        st.error("🚨 Situação crítica: múltiplas falhas detectadas!")
    elif len(falhas) > 0:
        st.warning(f"❌ {len(falhas)} falhas detectadas")

    if len(alto) > 0:
        st.warning(f"⚠️ {len(alto)} backups com alto consumo ( >= 200GB)")

    if len(risco_alto) > 0:
        st.warning(f"🔥 {len(risco_alto)} itens com risco elevado")

    st.markdown("---")

    # KPIs
    total = len(df)
    falhas_total = len(falhas)

    col1, col2 = st.columns(2)

    col1.metric("Sucesso", total - falhas_total, delta="OK")
    col2.metric("Falhas", falhas_total, delta="- Problema", delta_color="inverse")

    # STATUS
    st.subheader("📊 Status dos Backups")

    status_df = df["Status"].value_counts().reset_index()
    status_df.columns = ["Status", "Qtd"]

    fig1 = px.bar(
        status_df,
        x="Status",
        y="Qtd",
        color="Status",
        text="Qtd",
        color_discrete_map={
            "Completed": "#22c55e",
            "Failed": "#ef4444"
        }
    )

    fig1.update_traces(textfont_size=30)
    fig1.update_traces(textposition="inside")
    fig1.update_layout(template="plotly_dark")
    st.plotly_chart(fig1, use_container_width=True)

    # TURNO
    st.subheader("🕐 Backups por Turno")

    turno_df = df["Turno"].value_counts().reset_index()
    turno_df.columns = ["Turno", "Qtd"]

    fig2 = px.pie(turno_df, names="Turno", values="Qtd", hole=0.5)
    fig2.update_layout(template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

    # CONSUMO
    st.subheader("💽 Grafico de Maiores Consumos (GB)")

    consumo = df.groupby("Backup")["GB"].sum().reset_index()
    consumo = consumo.sort_values("GB", ascending=True).tail(10)
    consumo["GB_Formatado"] = consumo["GB"].apply(lambda x: f"{x:.1f} GB")

    fig3 = px.bar(
    consumo,
    x="GB",
    y="Backup",
    orientation="h",
    color="GB",
    color_continuous_scale="Reds",
    text="GB_Formatado"
)
    
    fig3.update_traces(textposition="outside")

    st.plotly_chart(fig3, use_container_width=True)

    # CRESCIMENTO
    st.subheader("📊 Tempo médio por Backup")

    tempo_df = (
    df.groupby("Backup")["Tempo_Minutos"]
    .mean()
    .reset_index()
)

    # pega os 10 mais demorados
    tempo_df = tempo_df.sort_values("Tempo_Minutos", ascending=True).tail(10)

    # formata para exibição
    tempo_df["Tempo_Formatado"] = tempo_df["Tempo_Minutos"].apply(
        lambda x: f"{int(x//60):02d}:{int(x%60):02d}:{int((x*60)%60):02d}"
    )


    fig4 = px.bar(
        tempo_df,
        x="Tempo_Minutos",
        y="Backup",
        orientation="h",
        color="Tempo_Minutos",
        color_continuous_scale="Reds",
        text="Tempo_Formatado"
    )

    fig4.update_traces(textposition="inside")

    st.plotly_chart(fig4, use_container_width=True)

# =========================
# 📋 DADOS
# =========================
with aba2:

    st.subheader("📋 Monitor de Backups")

    colunas_ordem = [
    "Tipo","Status_Icone","Status_Descricao","Backup","Categoria","Turno",
    "Modo","Inicio","Fim","Duracao","Tempo_Formatado",
    "Nivel","Percentual","Tamanho","Usuario"
]

    colunas_ordem = [c for c in colunas_ordem if c in df.columns]

    df_ordenado = df.sort_values("Inicio", ascending=False)

    if not df_ordenado.empty:
     ultimo = df_ordenado.iloc[0]
     st.info(f"🕒 Último backup: {ultimo['Backup']} às {ultimo['Inicio'].strftime('%d/%m/%Y %H:%M')}")

    st.dataframe(
    df_ordenado[colunas_ordem]
    .rename(columns={"Status_Icone": "Status","Status_Descricao": "Estado","Tempo_Formatado": "Tempo Execução" })
    .style
    .apply(destacar_processando, axis=1)
    .map(destaque_tamanho, subset=["Tamanho"])
    .map(destaque_status, subset=["Status"])
    .map(destaque_estado, subset=["Estado"])
    .set_properties(subset=["Status"], **{"text-align": "center"}),
    use_container_width=True
)


    st.markdown("---")

    # =========================
    # 🚨 FALHAS (NOVO)
    # =========================
    st.subheader("🚨 Backups com Falha")

    falhas_df = df[df["Status"].isin(["Failed", "Completed/Failures"])]

    if falhas_df.empty:
        st.success("Nenhuma falha encontrada 🎉")
    else:
        st.error(f"{len(falhas_df)} falhas encontradas!")
        falhas_df_ordenado = falhas_df.sort_values("Inicio", ascending=False)

        st.dataframe(
    falhas_df_ordenado[colunas_ordem]
    .rename(columns={
        "Status_Icone": "Status",
        "Status_Descricao": "Estado",
        "Tempo_Formatado": "Tempo Execução"})
    .style
    .map(destaque_status, subset=["Status"])
    .map(destaque_estado, subset=["Estado"]),
    use_container_width=True
)

        csv = falhas_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "⬇️ Exportar falhas (CSV)",
            data=csv,
            file_name="falhas_backup.csv",
            mime="text/csv"
        )

    st.markdown("---")


    # =========================
    # ⚠️ ALTO CONSUMO
    # =========================
    st.subheader("💽 Backups com Alto Consumo ( ≥ 200GB )")

    alto_df = df[df["GB"] >= 200]
    alto_df = alto_df.sort_values("GB", ascending=False)  

    if alto_df.empty:
        st.success("Nenhum alto consumo detectado")
    else:
     st.warning(f"{len(alto_df)} backups com alto consumo")

    st.dataframe(
        alto_df[colunas_ordem]
        .rename(columns={
            "Status_Icone": "Status",
            "Status_Descricao": "Estado",
             "Tempo_Formatado": "Tempo Execução"})
        .style
        .map(destaque_status, subset=["Status"])
        .map(destaque_estado, subset=["Estado"])
        .map(destaque_tamanho, subset=["Tamanho"])
        .set_properties(subset=["Status", "Estado"], **{"text-align": "center"}),
        use_container_width=True
    )

    st.markdown("---")

# =========================
#     # ⚠️ TIMELINE BACKUPS
# =========================

with aba3:

    st.subheader("⏰ Timeline de Backups")

    import pandas as pd
    from datetime import datetime, timedelta

    agora = datetime.now()

    # =========================
    # 📥 LÊ EXCEL
    # =========================
    try:
        df_agenda = pd.read_excel("agenda_backups.xlsx")
    except Exception as e:
        st.error(f"Erro ao carregar Excel: {e}")
        st.stop()

    df_agenda.columns = df_agenda.columns.str.strip()

    import unicodedata
    def normalizar(texto):
            texto = str(texto).strip().lower()
            texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
            return texto

    df_agenda["Tipo_Normalizado"] = df_agenda["Tipo"].apply(normalizar)

    # =========================
    # 🔧 FUNÇÃO
    # =========================
    def gerar_data(row):
        try:
            hora_txt = str(row["Hora"]).replace("h", "").strip()

            if ":" in hora_txt:
                hora, minuto = map(int, hora_txt.split(":"))
            else:
                hora = int(hora_txt)
                minuto = 0

            if str(row["Tipo"]).lower() == "diario":
                data_exec = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)

                if data_exec <= agora:
                    data_exec += timedelta(days=1)

            else:
                dias_semana = {
                    "segunda-feira": 0,
                    "terca-feira": 1,
                    "terça-feira": 1,
                    "quarta-feira": 2,
                    "quinta-feira": 3,
                    "sexta-feira": 4,
                    "sabado": 5,
                    "sábado": 5,
                    "domingo": 6
                }

                dia = str(row["Agendamento"]).strip().lower()
                dia_semana = dias_semana.get(dia)

                if dia_semana is None:
                    return None

                dias_para = (dia_semana - agora.weekday()) % 7

                data_exec = agora + timedelta(days=dias_para)
                data_exec = data_exec.replace(hour=hora, minute=minuto, second=0, microsecond=0)

                if data_exec <= agora:
                    data_exec += timedelta(days=7)

            return data_exec

        except:
            return None

    # =========================
    # 📊 PROCESSAMENTO
    # =========================
    df_agenda["Execucao"] = df_agenda.apply(gerar_data, axis=1)
    df_agenda = df_agenda.dropna(subset=["Execucao"])

    if df_agenda.empty:
        st.warning("Nenhum backup encontrado")
        st.stop()

    proximos = df_agenda.sort_values("Execucao").head(10)

    proximos["Hora"] = proximos["Execucao"].dt.strftime("%H:%M")
    proximos["Minutos"] = ((proximos["Execucao"] - agora).dt.total_seconds() / 60).astype(int)

    # =========================
    # ⏱️ TEMPO FORMATADO
    # =========================
    proximos["Tempo Restante"] = proximos["Minutos"].apply(
        lambda x: f"{x//60}h {x%60}m"
    )

    # =========================
    # 🚨 STATUS
    # =========================
    def classificar_status(minutos):
        if minutos <= 30:
            return "🔴 Crítico"
        elif minutos <= 120:
            return "🟡 Atenção"
        else:
            return "🟢 Normal"

    proximos["Status"] = proximos["Minutos"].apply(classificar_status)

    # =========================
    # 🔥 DESTAQUE PRINCIPAL
    # =========================
    proximo = proximos.iloc[0]

    st.markdown("## 🕒 Próximos Backups")

    st.success(
        f"{proximo['Hora']} → {proximo['Backup Specification']} "
        f"(em {proximo['Tempo Restante']})"
    )

    # =========================
    # 🚨 ALERTA CRÍTICO
    # =========================
    criticos = proximos[proximos["Minutos"] <= 30]

    if len(criticos) > 0:
        st.error(f"🚨 {len(criticos)} backup(s) iniciando em menos de 30 minutos!")

    # =========================
    # 📋 FILA VISUAL
    # =========================
    criticos = proximos[proximos["Minutos"] <= 120]
    outros = proximos[proximos["Minutos"] > 120]

    st.markdown("## 📋 Fila de Execução")

    # 🔴 CRÍTICOS / ATENÇÃO
    if not criticos.empty:
        st.markdown("### 🔴 Próximos Backups dentro de 2H")

        for _, row in criticos.iterrows():
            tempo = row["Minutos"]
            texto = f"[{row['Hora']}] {row['Backup Specification']} → {row['Tempo Restante']}"

            if tempo <= 30:
                st.error(f"⏳ {texto} | CRÍTICO")
            else:
                st.warning(f"⏱️ {texto} | ATENÇÃO")

    # 🟢 NORMAIS
    if not outros.empty:
        st.markdown("### 🟢 Proximos Agendados")

        for _, row in outros.iterrows():
            texto = f"[{row['Hora']}] {row['Backup Specification']} → {row['Tempo Restante']}"
            st.success(f"🕒 {texto} | NORMAL")

    # =========================
    # 📅 SEPARAÇÃO POR TIPO
    # =========================

    
    # =========================
    # 📅 BACKUPS DIÁRIOS
    # =========================
    st.markdown("## 📅 Backups Diários")

    diarios = proximos[proximos["Tipo"].str.lower() == "diario"]

    for _, row in diarios.iterrows():
        st.write(f"{row['Hora']} → {row['Backup Specification']}")


    # =========================
    # 🗓️ BACKUPS SEMANAIS (FORA DO LOOP)
    # =========================
    st.markdown("## 🗓️ Backups Semanais")

    df_agenda = pd.read_excel(
        "agenda_backups.xlsx",
        sheet_name="INVENTARIO SPECS",
        header=0
    )

    df_agenda.columns = df_agenda.columns.str.strip()

    semanais = df_agenda[
        df_agenda["Tipo"].str.strip().str.lower() == "semanal"
    ]

    colunas_exibir = [
        "Backup Specification",
        "Agendamento",
        "Janela/turno",
        "Hora",
        "Destino",
        "Observação",
        "VM´S"
    ]

    semanais = semanais[colunas_exibir]

    st.dataframe(semanais, use_container_width=True)