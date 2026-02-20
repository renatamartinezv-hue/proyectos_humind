import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(layout="wide")
st.title("Interactive Multi-Project Gantt Chart")

# === 1. CONFIGURA TU GOOGLE SHEET AQUÍ ===
# Pega tu URL COMPLETA de Google Sheets aquí:
SHEET_URL = "https://docs.google.com/spreadsheets/d/1O8aZdaPzIiYDreFA_9yRdfjOd9oMRy2TpAnl3mDwTBY/edit" 

TAB_NAME = "Sheet1" 
# ============================================

conn = st.connection("gsheets", type=GSheetsConnection)
default_start = datetime(2026, 2, 19).date()

# 2. Lógica de Base de Datos
try:
    df = conn.read(spreadsheet=SHEET_URL, worksheet=TAB_NAME, ttl=0)
    df = df.dropna(how="all") 
    
    if df.empty:
        # Actualizamos los datos por defecto para incluir el Nombre del Proyecto
        st.session_state['tasks'] = pd.DataFrame([
            {"Task ID": "T1", "Project Name": "Proyecto 1", "Task Name": "Project Kickoff", "Duration (Days)": 2, "Depends On": None, "Start Date": default_start},
            {"Task ID": "T2", "Project Name": "Proyecto 1", "Task Name": "Market Research", "Duration (Days)": 5, "Depends On": "T1", "Start Date": None},
            {"Task ID": "T3", "Project Name": "Proyecto 2", "Task Name": "Design Phase", "Duration (Days)": 4, "Depends On": None, "Start Date": default_start},
        ])
    else:
        df["Start Date"] = pd.to_datetime(df["Start Date"], errors='coerce').dt.date
        st.session_state['tasks'] = df

except Exception as e:
    st.error(f"Error de conexión con Google Sheets: {e}")
    st.stop()

st.write("### 1. Edita el Calendario de Proyectos")

# 3. Editor de Datos (¡Agregamos la nueva columna de Proyecto!)
edited_df = st.data_editor(
    st.session_state['tasks'], 
    num_rows="dynamic", 
    width="stretch",
    column_config={
        "Task ID": st.column_config.TextColumn("Task ID", required=True),
        "Project Name": st.column_config.TextColumn("Project Name", required=True), # Nueva columna
        "Task Name": st.column_config.TextColumn("Task Name", required=True),
        "Duration (Days)": st.column_config.NumberColumn("Duration (Days)", min_value=1, step=1, required=True),
        "Depends On": st.column_config.TextColumn("Depends On (Task ID)"),
        "Start Date": st.column_config.DateColumn("Start Date", format="YYYY-MM-DD"),
    }
)

if st.button("💾 Guardar Cambios en Google Sheets"):
    try:
        conn.update(spreadsheet=SHEET_URL, worksheet=TAB_NAME, data=edited_df)
        st.success("¡Base de datos actualizada con éxito!")
        st.cache_data.clear() 
    except Exception as e:
        st.error(f"Error al guardar: {e}")

st.write("### 2. Línea de Tiempo de Proyectos")

calculated_data = {}

try:
    for index, row in edited_df.iterrows():
        t_id = str(row["Task ID"])
        t_project = row["Project Name"] # Capturamos el proyecto
        t_pre = row["Depends On"]
        t_duration = int(row["Duration (Days)"])
        t_manual_start = row["Start Date"]
        
        # Lógica para saber si es independiente para mostrarlo en el gráfico
        if pd.isna(t_pre) or t_pre is None or str(t_pre).strip() == "":
            dependency_text = "Independiente 🟢"
            if pd.notna(t_manual_start):
                t_start = t_manual_start
            else:
                t_start = default_start
        else:
            dependency_text = f"Depende de: {t_pre} 🔗"
            earliest_start = calculated_data[str(t_pre)]["Finish"] 
            
            if pd.notna(t_manual_start) and t_manual_start > earliest_start:
                t_start = t_manual_start
            else:
                t_start = earliest_start
            
        t_end = t_start + timedelta(days=t_duration)
        
        calculated_data[t_id] = {
            "Project": t_project,
            "Task": row["Task Name"],
            "Start": t_start,
            "Finish": t_end,
            "Dependency Info": dependency_text # Nueva información para la etiqueta interactiva
        }
        
    final_df = pd.DataFrame(list(calculated_data.values()))
    
    # 4. Graficar el Diagrama de Gantt
    fig = px.timeline(
        final_df, 
        x_start="Start", 
        x_end="Finish", 
        y=["Project", "Task"], # ¡Esto agrupa mágicamente las tareas por Proyecto en el eje Y!
        color="Project",       # Cada proyecto tendrá un color distinto automáticamente
        hover_data=["Dependency Info"], # Mostramos si tiene dependencias al pasar el mouse
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(plot_bgcolor='white')
    fig.update_xaxes(
        showgrid=True, 
        gridcolor='lightgray', 
        gridwidth=1,
        tickformat="%b %d, %Y"
    )
    
    st.plotly_chart(fig, width="stretch", use_container_width=True)

except KeyError as e:
    st.error(f"**Error de Dependencia:** Revisa tu columna 'Depends On'. La tarea {e} no existe o se calculó en el orden incorrecto.")
except Exception as e:
    st.error("Por favor asegúrate de llenar todos los campos correctamente.")
