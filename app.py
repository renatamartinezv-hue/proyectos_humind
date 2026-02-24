!pip install streamlit pandas plotly
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configuración básica de Streamlit
st.set_page_config(page_title="Mi Gráfico de Gantt", layout="wide")
st.title("📊 Gráfico de Gantt Dinámico")

# 1. DATOS DE PRUEBA (Esto luego será reemplazado por tu Google Sheet)
# Usamos fechas con formato de hora para permitir múltiples tareas en el mismo día
data = {
    "ID": ["T1", "T2", "T3", "T4"],
    "Fase": ["Proyecto Alpha", "Proyecto Alpha", "Proyecto Beta", "Independiente"],
    "Tarea": ["Investigación", "Desarrollo", "Diseño", "Actualizar Servidor"],
    "Inicio": ["2026-02-20 09:00", "2026-02-22 10:00", "2026-02-24 14:00", "2026-02-23 08:00"],
    "Fin": ["2026-02-21 17:00", "2026-02-25 18:00", "2026-02-26 18:00", "2026-02-23 12:00"],
    "Horas_Estimadas": [16, 32, 20, 4],
    "Responsable": ["Ana", "Carlos", "Ana", "Luis"],
    "Estado": ["Completado", "En progreso", "Pendiente", "Pendiente"],
    "Color": ["#2ECC71", "#3498DB", "#9B59B6", "#F1C40F"], # Verde, Azul, Morado, Amarillo
    "Dependencia": ["", "T1", "", ""]
}

df = pd.DataFrame(data)
df["Inicio"] = pd.to_datetime(df["Inicio"])
df["Fin"] = pd.to_datetime(df["Fin"])

# Calculamos días y horas totales dinámicamente
df["Dias_Duracion"] = (df["Fin"] - df["Inicio"]).dt.days
df["Dias_Duracion"] = df["Dias_Duracion"].apply(lambda x: x if x > 0 else 1) # Mínimo 1 día

# 2. ESTADÍSTICAS
st.header("📈 Estadísticas Generales")
col1, col2, col3, col4 = st.columns(4)

total_horas = df["Horas_Estimadas"].sum()
horas_completadas = df[df["Estado"] == "Completado"]["Horas_Estimadas"].sum()
tareas_totales = len(df)
tareas_completadas = len(df[df["Estado"] == "Completado"])

col1.metric("Total Horas Estimadas", f"{total_horas} hrs")
col2.metric("Horas Completadas", f"{horas_completadas} hrs")
col3.metric("Total Tareas", tareas_totales)
col4.metric("Tareas Completadas", tareas_completadas)

# Estadísticas por Proyecto (Fase)
st.subheader("Estadísticas por Proyecto")
stats_proyecto = df.groupby("Fase").agg({
    "Horas_Estimadas": "sum",
    "Dias_Duracion": "sum"
}).reset_index()
st.dataframe(stats_proyecto, use_container_width=True)

# 3. GRÁFICO DE GANTT (PLOTLY)
st.header("📅 Cronograma")

# Crear el gráfico base
fig = px.timeline(
    df, 
    x_start="Inicio", 
    x_end="Fin", 
    y="Tarea", 
    color="Color", # Usa el color definido en los datos
    color_discrete_map="identity", # Respeta los códigos HEX exactos
    hover_name="Fase",
    hover_data={
        "Color": False,
        "Inicio": "|%Y-%m-%d %H:%M",
        "Fin": "|%Y-%m-%d %H:%M",
        "Horas_Estimadas": True,
        "Dias_Duracion": True,
        "Responsable": True,
        "Estado": True
    },
    text="Responsable" # Muestra el responsable dentro de la barra
)

# Invertir el eje Y para que la primera tarea salga arriba
fig.update_yaxes(autorange="reversed")

# Agregar línea del "Día de Hoy"
hoy = datetime.now()
fig.add_vline(x=hoy, line_width=2, line_dash="dash", line_color="red", 
              annotation_text="Hoy", annotation_position="top left")

# Agregar hitos (Milestones) para tareas completadas
completadas = df[df["Estado"] == "Completado"]
if not completadas.empty:
    fig.add_trace(go.Scatter(
        x=completadas["Fin"], 
        y=completadas["Tarea"],
        mode="markers",
        marker=dict(symbol="star", size=15, color="gold", line=dict(width=2, color="black")),
        name="Hito Completado",
        hoverinfo="skip"
    ))

# Formatear el gráfico para que se vea limpio
fig.update_layout(
    xaxis_title="Fecha y Hora",
    yaxis_title="Tareas (por Fase)",
    showlegend=False,
    height=500
)

# Mostrar el gráfico en Streamlit
st.plotly_chart(fig, use_container_width=True)
