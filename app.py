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
            
        t_manual_start = pd.to_datetime(row["Start Date"]).date() if pd.notna(row["Start Date"]) else None
        
        if t_pre == "" or t_pre.lower() == "none" or t_pre == "nan":
            dependency_text = "Independiente 🟢"
            t_start = t_manual_start if t_manual_start else default_start
        else:
            dependency_text = f"Depende de: {t_pre} 🔗"
            if t_pre in calculated_data:
                earliest_start = pd.to_datetime(calculated_data[t_pre]["Finish"]).date()
            else:
                earliest
