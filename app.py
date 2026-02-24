import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(layout="wide")
st.title("Gantt Interactivo Multientrega")

# === 1. CONFIGURA TU GOOGLE SHEET AQUÍ ===
SHEET_URL = "PASTE_YOUR_LONG_URL_HERE" 
TAB_NAME = "Sheet1" 
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

conn = st.connection("gsheets", type=GSheetsConnection)
hoy = datetime.today().date()
default_start = pd.to_datetime(hoy)

# 2. Lógica de Base de Datos y Limpieza
try:
    df = conn.read(spreadsheet=SHEET_URL, worksheet=TAB_NAME, ttl=0)
    df = df.dropna(how="all") 
    
    if df.empty:
        st.session_state['tasks'] = pd.DataFrame([
            {"Task ID": "T1", "Parent Task ID": None, "Project Name": "Proyecto Alfa", "Task Name": "Fase de Desarrollo", "Depends On": None, "Duration (Days)": 7, "Start Date": hoy, "Horas Invertidas": 0, "Responsable(s)": "Equipo Tech", "Notas Extra": "", "Color": "Gris"},
            {"Task ID": "T2", "Parent Task ID": "T1", "Project Name": "Proyecto Alfa", "Task Name": "Frontend", "Depends On": None, "Duration (Days)": 3, "Start Date": hoy, "Horas Invertidas": 40, "Responsable(s)": "Carlos M.", "Notas Extra": "", "Color": "Azul"},
            {"Task ID": "T3", "Parent Task ID": "T1", "Project Name": "Proyecto Alfa", "Task Name": "Backend", "Depends On": "T2", "Duration (Days)": 4, "Start Date": None, "Horas Invertidas": 35, "Responsable(s)": "Ana P.", "Notas Extra": "", "Color": "Rojo"},
            {"Task ID": "T4", "Parent Task ID": None, "Project Name": "Proyecto Beta", "Task Name": "Lanzamiento", "Depends On": None, "Duration (Days)": 5, "Start Date": hoy + pd.Timedelta(days=10), "Horas Invertidas": 15, "Responsable(s)": "Dirección", "Notas Extra": "", "Color": "Verde"},
            {"Task ID": "T5", "Parent Task ID": None, "Project Name": "Proyecto Beta", "Task Name": "Reunión Flash", "Depends On": None, "Duration (Days)": 1, "Start Date": hoy + pd.Timedelta(days=10), "Horas Invertidas": 2, "Responsable(s)": "Todos", "Notas Extra": "Tarea de 1 solo día", "Color": "Amarillo"},
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
                df[col] = df[col].astype(str).replace(["nan", "None", "NaN"], None)
                
        if "Horas Invertidas" in df.columns:
            df["Horas Invertidas"] = pd.to_numeric(df["Horas Invertidas"], errors='coerce').fillna(0)
            
        if "Duration (Days)" in df.columns:
            df["Duration (Days)"] = pd.to_numeric(df["Duration (Days)"], errors='coerce').fillna(1).astype(int)
            
        if "Start Date" in df.columns:
            df["Start Date"] = pd.to_datetime(df["Start Date"], errors='coerce').dt.date
            
        st.session_state['tasks'] = df

except Exception as e:
    st.error(f"Error de conexión con Google Sheets: {e}")
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
            # === TAREA PADRE ===
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
            # === TAREA HIJA / INDEPENDIENTE ===
            dep_id = data["Depends_On_ID"]
            manual_s = data["Manual_Start"]
            dur = data["Manual_Duration"]
            
            if dep_id and dep_id in calculated_data:
                _, dep_f = compute_dates(dep_id)
                s = dep_f # INICIA EXACTAMENTE AL TERMINAR SU DEPENDENCIA
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
        
    padres_ids = set([data["Parent Task ID"] for t_id, data in calculated_data.items() if data["Parent Task ID"]])

    def get_root_task(task_id, visited_nodes=None):
        if visited_nodes is None: visited_nodes = set()
        if task_id in visited_nodes: return task_id 
        visited_nodes.add(task_id)
        if task_id not in calculated_data: return task_id
        pred_id = calculated_data[task_id].get("Depends_On_ID", "")
        if not pred_id or pred_id not in calculated_data: return task_id
        if calculated_data[task_id]["Parent Task ID"] != calculated_data[pred_id]["Parent Task ID"]: return task_id
        return get_root_task(pred_id, visited_nodes)

    for tid, data in calculated_data.items():
        if data["Parent Task ID"]: 
            root_id = get_root_task(tid)
            calculated_data[tid]["Root_ID"] = root_id
            if root_id in calculated_data:
                root_name = calculated_data[root_id]["Task Name"]
                calculated_data[tid]["Track_Name"] = f"   ↳ Ruta: {root_name}"
            else:
                calculated_data[tid]["Track_Name"] = f"   ↳ Subtareas"

except Exception as e:
    st.error(f"Error procesando relaciones: {e}")

if st.button("💾 Guardar Cambios en Google Sheets"):
    try:
        df_to_save = edited_df.copy()
        for index, row in df_to_save.iterrows():
            t_id = str(row["Task ID"]).strip()
            if t_id in calculated_data:
                df_to_save.at[index, "Start Date"] = calculated_data[t_id]["Original_Start"].date()
                if calculated_data[t_id]["Dependency Info"] == "Tarea Padre 📂":
                    df_to_save.at[index, "Duration (Days)"] = calculated_data[t_id]["Duration"]
                    df_to_save.at[index, "Horas Invertidas"] = calculated_data[t_id]["Horas Invertidas"]
                    
        # Limpiar End Date si quedo del intento anterior
        if "End Date" in df_to_save.columns:
            df_to_save = df_to_save.drop(columns=["End Date"])

        conn.update(spreadsheet=SHEET_URL, worksheet=TAB_NAME, data=df_to_save)
        st.success("¡Base de datos actualizada! Todas las fechas encajan perfectamente a través de la duración.")
        st.cache_data.clear() 
    except Exception as e:
        st.error(f"Error al guardar: {e}")

try:
    final_tasks = []
    fecha_hoy_segura = pd.to_datetime(hoy)
    
    for t_id, data in calculated_data.items():
        o_start = data["Original_Start"]
        o_finish = data["Original_Finish"]
        
        if o_start.date() < hoy and o_finish.date() > hoy:
            final_tasks.append({**data, "Start": o_start, "Finish": fecha_hoy_segura, "Status": "Pasado", "Hide_Label": True})
            final_tasks.append({**data, "Start": fecha_hoy_segura, "Finish": o_finish, "Status": "Activo", "Hide_Label": False})
        elif o_finish.date() <= hoy:
            final_tasks.append({**data, "Start": o_start, "Finish": o_finish, "Status": "Pasado", "Hide_Label": False})
        else:
            final_tasks.append({**data, "Start": o_start, "Finish": o_finish, "Status": "Activo", "Hide_Label": False})
            
    final_df = pd.DataFrame(final_tasks)
    
    if not final_df.empty:
        # Generar espacio visual restando unas horitas al grafico (solo visual)
        def adjust_finish_for_plot(row):
            if row["Finish"] == row["Original_Finish"]:
                return row["Finish"] - pd.Timedelta(hours=3)
            return row["Finish"]
            
        final_df["Plot_Finish"] = final_df.apply(adjust_finish_for_plot, axis=1)
        
        def get_sort_key(row_data):
            p_id = row_data["Parent Task ID"]
            t_id = row_data["Task ID"]
            
            if p_id and p_id in calculated_data:
                parent_start = calculated_data[p_id]["Original_Start"].timestamp()
                root_id = row_data.get("Root_ID", t_id)
                if root_id in calculated_data:
                    root_start = calculated_data[root_id]["Original_Start"].timestamp()
                else:
                    root_start = row_data['Original_Start'].timestamp()
                return f"{parent_start}_1_{root_start}_{root_id}" 
            elif t_id in padres_ids:
                return f"{row_data['Original_Start'].timestamp()}_0_0_{t_id}"
            else:
                return f"{row_data['Original_Start'].timestamp()}_0_0_{t_id}"

        final_df["Sort_Key"] = final_df.apply(get_sort_key, axis=1)
        
        # Orden Cronológico de Proyectos
        project_starts = final_df.groupby("Project Name")["Original_Start"].min().to_dict()
        final_df["Project_Min_Start"] = final_df["Project Name"].map(project_starts)
        final_df = final_df.sort_values(by=["Project_Min_Start", "Project Name", "Sort_Key", "Original_Start"])
        
        def get_y_axis_name(row_data):
            p_id = row_data["Parent Task ID"]
            t_id = row_data["Task ID"]
            
            if p_id and p_id in calculated_data:
                return row_data.get("Track_Name", f"   ↳ Subtareas")
            elif t_id in padres_ids:
                return f"📂 {row_data['Task Name']}"
            else:
                return row_data["Task Name"]

        final_df["Llave_Secreta"] = final_df["Project Name"].astype(str) + "|||" + final_df.apply(get_y_axis_name, axis=1)
        
        # Strings para etiquetas visuales
        final_df["Orig_Start_str"] = final_df["Original_Start"].dt.strftime('%d %b')
        # El display finish es 1 día menos para que cuadre con la logica humana (ej. empieza 1 y dura 1 dia -> termina 1)
        final_df["Display_Finish_str"] = (final_df["Original_Finish"] - pd.Timedelta(days=1)).dt.strftime('%d %b')
        
        def generar_label(x):
            if x.get("Hide_Label", False): return ""
            return (
                f"<b>{x['Project Name']} - {x['Task Name']}</b><br>"
                f"{x['Orig_Start_str']} a {x['Display_Finish_str']} - {x['Duration']} días<br>"
                f"{x['Horas Invertidas']} hrs<br>"
                f"{x['Responsable(s)']}"
            )

        final_df["Label"] = final_df.apply(generar_label, axis=1)
        final_df["Color_Key"] = final_df.apply(lambda row: f"{row['Task ID']} (Completado)" if row["Status"] == "Pasado" else row["Task ID"], axis=1)
        
        color_map = {} 
        pastel_colors = px.colors.qualitative.Pastel
        color_idx = 0
        project_default_colors = {}
        for p in final_df["Project Name"].unique():
            project_default_colors[p] = pastel_colors[color_idx % len(pastel_colors)]
            color_idx += 1
            
        for index, row in final_df.iterrows():
            tid = row["Task ID"]
            active_key = tid
            past_key = f"{tid} (Completado)"
            
            if active_key not in color_map:
                user_color = str(row.get("Color_Raw", "Por defecto")).strip()
                if user_color != "Por defecto" and user_color in COLOR_MAP_ESP:
                    base_color = COLOR_MAP_ESP[user_color]
                else:
                    base_color = project_default_colors.get(row["Project Name"], "#3366cc")
                    
                color_map[active_key] = base_color
                
                c_str = str(base_color).strip().lower()
                try:
                    if c_str.startswith('#'):
                        hex_c = c_str.lstrip('#')
                        if len(hex_c) == 3: hex_c = "".join([c*2 for c in hex_c])
                        r, g, b = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
                    else:
                        r, g, b = 150, 150, 150
                    muted_color = f'rgba({r},{g},{b}, 0.3)'
                except Exception:
                    muted_color = "rgba(211,211,211, 0.3)"
                
                color_map[past_key] = muted_color
    
    st.write("---") 
    st.write("### 📊 Resumen del Portafolio")
    
    if not final_df.empty:
        fecha_inicio_global = final_df["Original_Start"].min()
        fecha_fin_global = final_df["Original_Finish"].max()
        
        dias_totales = (fecha_fin_global - fecha_inicio_global).days
        dias_restantes = max(0, (fecha_fin_global.date() - hoy).days)
        tareas_unicas = len([t for t, d in calculated_data.items() if t not in padres_ids])
        total_horas = sum([d["Horas Invertidas"] for t, d in calculated_data.items() if t not in padres_ids])
        
        tareas_activas = 0
        proyectos_stats = {}
        
        for t_id, data in calculated_data.items():
            o_start = data["Original_Start"].date()
            o_finish = data["Original_Finish"].date()
            
            if t_id not in padres_ids:
                if o_start <= hoy < o_finish:
                    tareas_activas += 1
                    
            proj = data["Project Name"]
            if proj not in proyectos_stats:
                proyectos_stats[proj] = {"inicio": o_start, "fin": o_finish}
            else:
                if o_start < proyectos_stats[proj]["inicio"]: proyectos_stats[proj]["inicio"] = o_start
                if o_finish > proyectos_stats[proj]["fin"]: proyectos_stats[proj]["fin"] = o_finish
                
        proyectos_activos = sum(1 for p, dates in proyectos_stats.items() if dates["inicio"] <= hoy < dates["fin"])

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("⏳ Duración Portafolio", f"{dias_totales} días")
        col2.metric("📅 Días Restantes", f"{dias_restantes} días")
        col3.metric("📝 Total de Tareas", tareas_unicas)
        col4.metric("⏱️ Horas Totales", f"{total_horas} hrs")
        col5.metric("🚀 Tareas Activas", tareas_activas)
        col6.metric("📂 Proyectos Activos", proyectos_activos)

    st.write("### 2. Línea de Tiempo de Proyectos")
    
    if not final_df.empty:
        fig = px.timeline(
            final_df, 
            x_start="Start", 
            x_end="Plot_Finish", 
            y="Llave_Secreta", 
            color="Color_Key", 
            color_discrete_map=color_map, 
            text="Label",     
            hover_data={
                "Color_Key": False,
                "Llave_Secreta": False,
                "Plot_Finish": False,
                "Project Name": True,
                "Parent Task ID": True,
                "Responsable(s)": True,
                "Dependency Info": True
            },
        )
        
        fig.update_traces(
            textfont_size=12, 
            textfont_color="black",
            textposition='inside', 
            insidetextanchor='middle'
        )
        
        for trace in fig.data:
            if getattr(trace, "y", None) is not None:
                proyectos = [str(val).split("|||")[0] for val in trace.y]
                tareas = [str(val).split("|||")[1] for val in trace.y]
                trace.y = [proyectos, tareas] 
                
        hitos_unicos = set()
        fechas_fin_proy = {}
        for idx, row in final_df.iterrows():
            p = row["Project Name"]
            f = row["Original_Finish"]
            t = row["Llave_Secreta"].split("|||")[1] 
            if p not in fechas_fin_proy or f > fechas_fin_proy[p]["fecha"]:
                fechas_fin_proy[p] = {"fecha": f, "tarea": t}
                
        for p, datos in fechas_fin_proy.items():
            hitos_unicos.add((p, datos["tarea"], datos["fecha"]))
            
        for idx, row in final_df.iterrows():
            if "Independiente" in row["Dependency Info"] and row["Task ID"] not in padres_ids:
                hitos_unicos.add((row["Project Name"], row["Llave_Secreta"].split("|||")[1], row["Original_Finish"]))
                
        hitos_x = []
        hitos_y_proy = []
        hitos_y_tarea = []
        
        for p, t, f in hitos_unicos:
            hitos_x.append(f)
            hitos_y_proy.append(p)
            hitos_y_tarea.append(t)
            
        fig.add_trace(go.Scatter(
            x=hitos_x,
            y=[hitos_y_proy, hitos_y_tarea],
            mode='markers+text',
            marker=dict(symbol='diamond', size=16, color='#FFD700', line=dict(color='black', width=1.5)),
            text=[" 🏁 Fin"] * len(hitos_x),
            textposition="middle right",
            textfont=dict(color="black", size=13, family="Arial Black"),
            hoverinfo='skip',
            showlegend=False
        ))

        fig.update_yaxes(
            autorange="reversed", 
            title_text="",
            type="multicategory",
            dividercolor="gray",  
            dividerwidth=1        
        )
        fig.layout.yaxis.categoryarray = None 
        
        unique_llaves = final_df["Llave_Secreta"].unique()
        proyectos_ordenados = [llave.split("|||")[0] for llave in unique_llaves]
        
        for i in range(1, len(proyectos_ordenados)):
            if proyectos_ordenados[i] != proyectos_ordenados[i-1]:
                fig.add_hline(
                    y=i - 0.5, 
                    line_width=1.5, 
                    line_dash="dot", 
                    line_color="gray", 
                    opacity=0.6
                )
        
        fig.update_layout(
            plot_bgcolor='white', 
            height=max(450, len(final_df['Llave_Secreta'].unique()) * 100),
            margin=dict(l=150, r=50),
            showlegend=False 
        ) 
        
        fig.update_xaxes(
            type='date',
            showgrid=True, 
            gridcolor='lightgray', 
            gridwidth=1,
            tickformat="%d %b %Y"
        )
        
        hoy_ms = int(pd.Timestamp(hoy).timestamp() * 1000)
        fecha_texto = hoy.strftime("%d/%m/%Y") 
        
        fig.add_vline(
            x=hoy_ms, 
            line_width=3, 
            line_dash="dash", 
            line_color="darkblue", 
            annotation_text=f" HOY ({fecha_texto}) ", 
            annotation_position="top right", 
            annotation_font_color="darkblue",
            annotation_font_size=14
        )
        
        st.plotly_chart(fig, width="stretch", use_container_width=True)
    else:
        st.info("No hay tareas válidas para mostrar en el gráfico.")

    st.write("---")
    
    st.write("### 📋 Reporte Final Descargable")
    with st.expander("Haz clic aquí para ver y descargar el reporte completo", expanded=True):
        
        table_data = []
        for t_id, data in calculated_data.items():
            o_start = data["Original_Start"]
            disp_finish = data["Original_Finish"] - pd.Timedelta(days=1)
            
            if data["Original_Finish"].date() <= hoy:
                status = "Completado ✅"
            elif o_start.date() > hoy:
                status = "Pendiente ⏳"
            else:
                status = "En Proceso 🔵"
                
            table_data.append({
                "ID": t_id,
                "Parent Task ID": data["Parent Task ID"] if data["Parent Task ID"] else "-",
                "Proyecto": data["Project Name"],
                "Tarea": data["Task Name"],
                "Responsable(s)": data["Responsable(s)"],
                "Horas": data["Horas Invertidas"],
                "Inicio": o_start.strftime("%d/%m/%Y"),
                "Fin": disp_finish.strftime("%d/%m/%Y"), 
                "Duración": f"{data['Duration']} días",
                "Estado": status,
                "Dependencia": data["Dependency Info"].replace("🔗", "").replace("🟢", "").replace("📂", "").strip(),
                "Notas Extra": data["Notas Extra"]
            })
        
        df_table = pd.DataFrame(table_data)
        
        st.dataframe(df_table, use_container_width=True, hide_index=True)
        
        csv = df_table.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Reporte Completo (Excel / CSV)",
            data=csv,
            file_name='reporte_cronograma.csv',
            mime='text/csv',
        )

except KeyError as e:
    st.error(f"**Error de Dependencia:** Revisa que el ID de la tarea a la que estás apuntando exista. Detalles: {e}")
except Exception as e:
    st.error(f"Hubo un problema procesando los datos. Detalles técnicos: {e}")
