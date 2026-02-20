import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
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
default_start = pd.to_datetime(hoy)

# 2. Lógica de Base de Datos y Limpieza
try:
    df = conn.read(spreadsheet=SHEET_URL, worksheet=TAB_NAME, ttl=0)
    df = df.dropna(how="all") 
    
    if df.empty:
        st.session_state['tasks'] = pd.DataFrame([
            {"Task ID": "T1", "Project Name": "Proyecto 1", "Task Name": "Project Kickoff", "Duration (Days)": 2, "Depends On": None, "Start Date": hoy},
            {"Task ID": "T2", "Project Name": "Proyecto 1", "Task Name": "Market Research", "Duration (Days)": 5, "Depends On": "T1", "Start Date": None},
            {"Task ID": "T3", "Project Name": "Proyecto 2", "Task Name": "Design Phase", "Duration (Days)": 4, "Depends On": None, "Start Date": hoy},
        ])
    else:
        # Limpieza estricta
        for col in ["Task ID", "Project Name", "Task Name", "Depends On"]:
            if col in df.columns:
                df[col] = df[col].astype(str).replace(["nan", "None", "NaN"], None)
                
        if "Duration (Days)" in df.columns:
            df["Duration (Days)"] = pd.to_numeric(df["Duration (Days)"], errors='coerce').fillna(1).astype(int)
            
        if "Start Date" in df.columns:
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
        # Ignorar filas vacías
        if pd.isna(row["Task ID"]) or str(row["Task ID"]).strip() == "None" or str(row["Task ID"]).strip() == "":
            continue
            
        t_id = str(row["Task ID"]).strip()
        t_project = str(row["Project Name"]).strip() if pd.notna(row["Project Name"]) and str(row["Project Name"]) != "None" else "Sin Proyecto"
        t_task = str(row["Task Name"]).strip()
        
        t_pre_raw = row["Depends On"]
        t_pre = str(t_pre_raw).strip() if pd.notna(t_pre_raw) and str(t_pre_raw) != "None" else ""
        
        try:
            t_duration = int(row["Duration (Days)"])
        except (ValueError, TypeError):
            t_duration = 1
            
        if pd.notna(row["Start Date"]) and row["Start Date"] != "":
            t_manual_start = pd.to_datetime(row["Start Date"])
        else:
            t_manual_start = None
        
        if t_pre == "" or t_pre.lower() == "none" or t_pre == "nan":
            dependency_text = "Independiente 🟢"
            t_start = t_manual_start if t_manual_start is not None else default_start
        else:
            dependency_text = f"Depende de: {t_pre} 🔗"
            if t_pre in calculated_data:
                earliest_start = calculated_data[t_pre]["Finish"]
            else:
                earliest_start = default_start 
            
            if t_manual_start is not None and t_manual_start > earliest_start:
                t_start = t_manual_start
            else:
                t_start = earliest_start
        
        t_start = pd.to_datetime(t_start)
        t_end = t_start + pd.Timedelta(days=t_duration)
        
        calculated_data[t_id] = {
            "Project": t_project,
            "Task": t_task,
            "Start": t_start,
            "Finish": t_end,
            "Dependency Info": dependency_text
        }
        
    final_df = pd.DataFrame(list(calculated_data.values()))
    
    if not final_df.empty:
        final_df = final_df.sort_values(by=["Project", "Start"])
        
        final_df["Start_str"] = final_df["Start"].dt.strftime('%d %b')
        final_df["Finish_str"] = final_df["Finish"].dt.strftime('%d %b')
        
        final_df["Label"] = final_df.apply(
            lambda x: f"{str(x['Task'])} ({str(x['Start_str'])} - {str(x['Finish_str'])})", 
            axis=1
        )
        
        final_df["Color_Visual"] = final_df["Project"].astype(str)
        
        color_map = {} 
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
            color="Color_Visual", 
            color_discrete_map=color_map, 
            text="Label",     
            hover_data=["Project", "Dependency Info"]
        )
        
        fig.update_traces(
            textfont_size=14, 
            textfont_color="black",
            textposition='inside', 
            insidetextanchor='middle'
        )
        
        fig.update_yaxes(autorange="reversed", categoryorder='array', categoryarray=final_df['Task'].tolist())
        fig.update_layout(plot_bgcolor='white', height=max(400, len(final_df) * 45)) 
        
        fig.update_xaxes(
            type='date',
            showgrid=True, 
            gridcolor='lightgray', 
            gridwidth=1,
            tickformat="%b %d, %Y"
        )
        
        # === LÍNEAS SEPARADORAS DE PROYECTOS ===
        lista_proyectos = final_df['Project'].tolist()
        for i in range(len(lista_proyectos) - 1):
            if lista_proyectos[i] != lista_proyectos[i+1]:
                fig.add_hline(y=i + 0.5, line_width=2, line_dash="solid", line_color="black", opacity=0.3)
        
        # === LÍNEA DE "HOY" CON FECHA DINÁMICA (DÍA/MES/AÑO) ===
        hoy_ms = int(pd.Timestamp(hoy).timestamp() * 1000)
        
        # Formateamos la fecha a texto: "día/mes/año"
        fecha_texto = hoy.strftime("%d/%m/%Y") 
        
        fig.add_vline(
            x=hoy_ms, 
            line_width=3, 
            line_dash="dash", 
            line_color="darkblue", 
            annotation_text=f" HOY ({fecha_texto}) ",  # <--- SE MOSTRARÁ COMO "HOY (20/02/2026)"
            annotation_position="top right", 
            annotation_font_color="darkblue",
            annotation_font_size=14
        )
        # ========================================================
        
        st.plotly_chart(fig, width="stretch", use_container_width=True)
    else:
        st.info("No hay tareas válidas para mostrar en el gráfico. ¡Agrega algunas en la tabla de arriba!")

except KeyError as e:
    st.error(f"**Error de Dependencia:** La tarea de la que dependes no se calculó bien. Detalles: {e}")
except Exception as e:
    st.error(f"Hubo un problema procesando los datos. Detalles técnicos: {e}")
