import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(layout="wide")
st.title("Interactive Multi-Project Gantt Chart")

# === 1. CONFIGURA TU GOOGLE SHEET AQUÍ ===
SHEET_URL = "https://docs.google.com/spreadsheets/d/1O8aZdaPzIiYDreFA_9yRdfjOd9oMRy2TpAnl3mDwTBY/edit" 
TAB_NAME = "Sheet1" 
# ============================================

conn = st.connection("gsheets", type=GSheetsConnection)
hoy = datetime.today().date()
default_start = hoy 

# 2. Lógica de Base de Datos
try:
    df = conn.read(spreadsheet=SHEET_URL, worksheet=TAB_NAME, ttl=0)
    df = df.dropna(how="all") 
    
    if df.empty:
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

# 3. Editor de Datos
edited_df = st.data_editor(
    st.session_state['tasks'], 
    num_rows="dynamic", 
    width="stretch",
    column_config={
        "Task ID": st.column_config.TextColumn("Task ID", required=True),
        "Project Name": st.column_config.TextColumn("Project Name", required=True), 
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

calculated_data = {}

try:
    for index, row in edited_df.iterrows():
        if pd.isna(row["Task ID"]):
            continue
            
        t_id = str(row["Task ID"]).strip()
        t_project = str(row["Project Name"]).strip() if pd.notna(row["Project Name"]) else "Sin Proyecto"
        t_task = str(row["Task Name"]).strip()
        
        t_pre_raw = row["Depends On"]
        t_pre = str(t_pre_raw).strip() if pd.notna(t_pre_raw) else ""
        
        try:
            t_duration = int(row["Duration (Days)"])
        except (ValueError, TypeError):
            t_duration = 1
            
        # Nos aseguramos de que el inicio manual sea una fecha real o None
        t_manual_start = pd.to_datetime(row["Start Date"]).date() if pd.notna(row["Start Date"]) else None
        
        if t_pre == "" or t_pre.lower() == "none" or t_pre == "nan":
            dependency_text = "Independiente 🟢"
            t_start = t_manual_start if t_manual_start else default_start
        else:
            dependency_text = f"Depende de: {t_pre} 🔗"
            if t_pre in calculated_data:
                # Extraemos la fecha garantizando que sea Date
                earliest_start = pd.to_datetime(calculated_data[t_pre]["Finish"]).date()
            else:
                earliest_start = default_start 
            
            if t_manual_start and t_manual_start > earliest_start:
                t_start = t_manual_start
            else:
                t_start = earliest_start
            
        t_end = t_start + timedelta(days=t_duration)
        
        calculated_data[t_id] = {
            "Project": t_project,
            "Task": t_task,
            "Start": t_start,
            "Finish": t_end,
            "Dependency Info": dependency_text
        }
        
    final_df = pd.DataFrame(list(calculated_data.values()))
    
    if not final_df.empty:
        # === AQUÍ ESTÁ LA SOLUCIÓN DEFINITIVA A TU DIAGNÓSTICO ===
        # Obligamos a que las columnas sean DATETIME nativo de Pandas antes de pasarlas a Plotly
        final_df["Start"] = pd.to_datetime(final_df["Start"])
        final_df["Finish"] = pd.to_datetime(final_df["Finish"])
        
        final_df = final_df.sort_values(by=["Project", "Start"])
        
        final_df["Start_str"] = final_df["Start"].dt.strftime('%d %b')
        final_df["Finish_str"] = final_df["Finish"].dt.strftime('%d %b')
        
        final_df["Label"] = final_df.apply(
            lambda x: f"{str(x['Task'])} ({str(x['Start_str'])} - {str(x['Finish_str'])})", 
            axis=1
        )
        
        # Como "Finish" ya es estrictamente Datetime, la lógica de Completado (Gris) es 100% segura
        final_df["Color_Visual"] = final_df.apply(
            lambda row: "Completado (Gris)" if row["Finish"].date() < hoy else str(row["Project"]), 
            axis=1
        )
        
        color_map = {"Completado (Gris)": "#d3d3d3"} 
        pastel_colors = px.colors.qualitative.Pastel
        color_idx = 0
        
        for p in final_df["Project"].unique():
            if p not in color_map:
                color_map[p] = pastel_colors[color_idx % len(pastel_colors)]
                color_idx += 1
    
    st.write("---") 
    st.write("### 📊 Resumen del Portafolio")
    
    if not final_df.empty:
        fecha_inicio_global = final_df["Start"].min()
        fecha_fin_global = final_df["Finish"].max()
        dias_totales = (fecha_fin_global - fecha_inicio_global).days
        
        col1, col2, col3 = st.columns(3)
        col1.metric("⏳ Duración Total", f"{dias_totales} días")
        col2.metric("📝 Total de Tareas", len(final_df))
        col3.metric("📁 Proyectos Activos", final_df["Project"].nunique())

    st.write("### 2. Línea de Tiempo de Proyectos")
    
    if not final_df.empty:
        fig = px.timeline(
            final_df, 
            x_start="Start", 
            x_end="Finish", 
            y="Task",
