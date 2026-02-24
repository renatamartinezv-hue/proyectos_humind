import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Configuración de la página
st.set_page_config(layout="wide")
st.title("Gantt Interactivo Multientrega")

# === 1. CONFIGURA TU GOOGLE SHEET Y JSON AQUÍ ===
SHEET_URL = "https://docs.google.com/spreadsheets/d/1O8aZdaPzIiYDreFA_9yRdfjOd9oMRy2TpAnl3mDwTBY/edit" 
TAB_NAME = "Sheet1" 
JSON_FILE_PATH = "credenciales.json" # <-- Pon aquí el nombre exacto de tu archivo JSON
# ============================================

# Diccionario de colores
COLOR_MAP_ESP = {
    "Por defecto": "",
    "Azul": "#4285F4",
    "Rojo": "#EA4335",
    "Verde": "#34A853",
    "Amarillo": "#FBBC05",
    "Naranja": "#FF6D01",
    "Morado": "#8E24AA",
    "Rosa": "#E91E63",
    "Gris": "#9E9E9E",
    "Cian": "#00BCD4"
}
opciones_color = list(COLOR_MAP_ESP.keys())

hoy = datetime.today().date()
default_start = pd.to_datetime(hoy)

# 2. Lógica de Base de Datos y Limpieza usando JSON
try:
    # Autenticación directa con tu archivo JSON
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(JSON_FILE_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL).worksheet(TAB_NAME)
    
    # Leer los datos
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df = df.dropna(how="all") 
    
    if df.empty:
        st.session_state['tasks'] = pd.DataFrame([
            {"Task ID": "T1", "Parent Task ID": None, "Project Name": "Proyecto Alfa", "Task Name": "Fase de Desarrollo", "Depends On": None, "Duration (Days)": 7, "Start Date": hoy, "Horas Invertidas": 0, "Responsable(s)": "Equipo Tech", "Notas Extra": "", "Color": "Gris"},
            {"Task ID": "T2", "Parent Task ID": "T1", "Project Name": "Proyecto Alfa", "Task Name": "Frontend", "Depends On": None, "Duration (Days)": 3, "Start Date": hoy, "Horas Invertidas": 40, "Responsable(s)": "Carlos M.", "Notas Extra": "", "Color": "Azul"},
            {"Task ID": "T3", "Parent Task ID": "T1", "Project Name": "Proyecto Alfa", "Task Name": "Backend", "Depends On": "T2", "Duration (Days)": 4, "Start Date": None, "Horas Invertidas": 35, "Responsable(s)": "Ana P.", "Notas Extra": "", "Color": "Rojo"}
        ])
    else:
        for col in ["Notas Extra", "Parent Task ID", "Responsable(s)"]:
            if col not in df.columns: df[col] = ""
            
        if "Horas Invertidas" not in df.columns: df["Horas Invertidas"] = 0
        if "Duration (Days)" not in df.columns: df["Duration (Days)"] = 1
        
        if "Color" not in df.columns:
            df["Color"] = "Por defecto"
        else:
            df["Color"] = df["Color"].apply(lambda x: x if x in opciones_color else "Por defecto")
            
        for col in ["Task ID", "Parent Task ID", "Project Name", "Task Name", "Responsable(s)", "Notas Extra", "Depends On"]:
            if col in df.columns:
                df[col] = df[col].astype(str).replace(["nan", "None", "NaN", ""], None)
                
        if "Horas Invertidas" in df.columns:
            df["Horas Invertidas"] = pd.to_numeric(df["Horas Invertidas"], errors='coerce').fillna(0)
            
        if "Duration (Days)" in df.columns:
            df["Duration (Days)"] = pd.to_numeric(df["Duration (Days)"], errors='coerce').fillna(1).astype(int)
            
        if "Start Date" in df.columns:
            df["Start Date"] = pd.to_datetime(df["Start Date"], errors='coerce').dt.date
            
        st.session_state['tasks'] = df

except Exception as e:
    st.error(f"Error de conexión con el archivo JSON o Google Sheets: {e}")
    st.stop()

st.write("### 1. Edita el Calendario de Proyectos")

# 3. Editor de Datos PRINCIPAL
orden_columnas = [
    "Task ID", 
    "Parent Task ID", 
    "Project Name", 
    "Task Name", 
    "Depends On", 
    "Duration (Days)", 
    "Start Date",
    "Horas Invertidas",
    "Responsable(s)",
    "Notas Extra", 
    "Color" 
]

edited_df = st.data_editor(
    st.session_state['tasks'], 
    num_rows="dynamic", 
    width="stretch",
    column_order=orden_columnas, 
    column_config={
        "Task ID": st.column_config.TextColumn("Task ID", required=True),
        "Parent Task ID": st.column_config.TextColumn("Parent Task ID (Padre)"),
        "Project Name": st.column_config.TextColumn("Project Name", required=True), 
        "Task Name": st.column_config.TextColumn("Task Name", required=True),
        "Depends On": st.column_config.TextColumn("Depends On (Task ID)"),
        "Duration (Days)": st.column_config.NumberColumn("Duración (Días)", min_value=1, step=1, required=True),
        "Start Date": st.column_config.DateColumn("Start Date", format="YYYY-MM-DD"),
        "Horas Invertidas": st.column_config.NumberColumn("Horas Invertidas", min_value=0),
        "Responsable(s)": st.column_config.TextColumn("Responsables"),
        "Notas Extra": st.column_config.TextColumn("Notas Extra"), 
        "Color": st.column_config.SelectboxColumn(
            "Color de Tarea", 
            options=opciones_color,
            default="Por defecto"
        ),
    }
)

# === 4. LÓGICA DE CÁLCULO DINÁMICO ===
calculated_data = {}

try:
    for index, row in edited_df.iterrows():
        if pd.isna(row["Task ID"]) or str(row["Task ID"]).strip() in ["None", ""]:
            continue
            
        t_id = str(row["Task ID"]).strip()
        t_parent_raw = row.get("Parent Task ID")
        t_parent = str(t_parent_raw).strip() if pd.notna(t_parent_raw) and str(t_parent_raw) not in ["None", "nan", "NaN", ""] else None
        
        t_project = str(row["Project Name"]).strip() if pd.notna(row["Project Name"]) and str(row["Project Name"]) != "None" else "Sin Proyecto"
        t_task = str(row["Task Name"]).strip()
        t_resp = str(row.get("Responsable(s)", "")).strip() if pd.notna(row.get("Responsable(s)")) else ""
        t_horas = float(row.get("Horas Invertidas", 0))
        t_notas = str(row.get("Notas Extra", "")).strip() if pd.notna(row.get("Notas Extra")) else ""
        t_color_raw = str(row.get("Color", "Por defecto")).strip()
        
        t_pre_raw = row["Depends On"]
        t_pre = str(t_pre_raw).strip() if pd.notna(t_pre_raw) and str(t_pre_raw) not in ["None", "nan", "NaN", ""] else ""
        
        t_manual_start = pd.to_datetime(row["Start Date"]) if pd.notna(row["Start Date"]) and row["Start Date"] != "" else None
        
        try:
            t_duration = int(row["Duration (Days)"])
        except (ValueError, TypeError):
            t_duration = 1
            
        calculated_data[t_id] = {
            "Task ID": t_id,
            "Parent Task ID": t_parent,
            "Project Name": t_project,
            "Task Name": t_task,
            "Responsable(s)": t_resp,
            "Horas Invertidas": t_horas,
            "Notas Extra": t_notas,
            "Color_Raw": t_color_raw, 
            "Manual_Start": t_manual_start,
            "Manual_Duration": max(1, t_duration),
            "Depends_On_ID": t_pre, 
            "Dependency Info": "",
            "Original_Start": None,
            "Original_Finish": None,
            "Duration": 0
        }

    visited = set()
    resolving = set()
    
    def compute_dates(tid):
        if tid in visited:
            return calculated_data[tid]["Original_Start"], calculated_data[tid]["Original_Finish"]
        if tid in resolving:
            s = calculated_data[tid]["Manual_Start"] if calculated_data[tid]["Manual_Start"] else default_start
            dur = calculated_data[tid]["Manual_Duration"]
            return s, s + pd.Timedelta(days=dur)
            
        resolving.add(tid)
        data = calculated_data[tid]
        
        hijos = [h_id for h_id, h_data in calculated_data.items() if h_data["Parent Task ID"] == tid]
        
        if hijos:
            min_s, max_f = None, None
            horas_totales = 0
            resps = set()
            
            for h in hijos:
                c_s, c_f = compute_dates(h)
                
                if min_s is None or c_s < min_s: min_s = c_s
                if max_f is None or c_f > max_f: max_f = c_f
                
                horas_totales += calculated_data[h]["Horas Invertidas"]
                if calculated_data[h]["Responsable(s)"]:
                    for r in str(calculated_data[h]["Responsable(s)"]).split(","):
                        if r.strip(): resps.add(r.strip())
            
            s = min_s if min_s else default_start
            f = max_f if max_f else (s + pd.Timedelta(days=1))
            dur = max(1, (f - s).days)
            
            calculated_data[tid]["Original_Start"] = s
            calculated_data[tid]["Original_Finish"] = f
            calculated_data[tid]["Duration"] = dur
            calculated_data[tid]["Horas Invertidas"] = horas_totales
            
            if not data["Responsable(s)"]:
                calculated_data[tid]["Responsable(s)"] = ", ".join(list(resps))
                
            calculated_data[tid]["Dependency Info"] = "Tarea Padre 📂"
            
        else:
            dep_id = data["Depends_On_ID"]
            manual_s = data["Manual_Start"]
            dur = data["Manual_Duration"]
            
            if dep_id and dep_id in calculated_data:
                _, dep_f = compute_dates(dep_id)
                s = dep_f 
                calculated_data[tid]["Dependency Info"] = f"Depende de: {dep_id} 🔗"
            else:
                s = manual_s if manual_s else default_start
                calculated_data[tid]["Dependency Info"] = "Independiente 🟢"
                
            f = s + pd.Timedelta(days=dur)
            
            calculated_data[tid]["Original_Start"] = s
            calculated_data[tid]["Original_Finish"] = f
            calculated_data[tid]["Duration"] = dur
            
        resolving.remove(tid)
        visited.add(tid)
        return calculated_data[tid]["Original_Start"], calculated_data[tid]["Original_Finish"]
        
    for tid in calculated_data:
        compute_dates(tid)
        
    pad
