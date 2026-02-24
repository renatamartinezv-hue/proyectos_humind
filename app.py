import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(layout="wide")
st.title("Diagnóstico 25 Empresas")

# === 1. CONFIGURA TU GOOGLE SHEET AQUÍ ===
SHEET_URL = "https://docs.google.com/spreadsheets/d/1O8aZdaPzIiYDreFA_9yRdfjOd9oMRy2TpAnl3mDwTBY/edit" 
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
            {"ID Fase": "T1", "Parent ID Fase": None, "Número de Fase": "Proyecto Alfa", "Nombre de Tarea": "Fase de Desarrollo", "Depende de (ID Fase)": None, "Duración (días)": 1, "Fecha de Inicio (solo si independiente)": hoy, "Horas Invertidas": 0, "Responsable(s)": "Equipo Tech", "Notas Extra": "", "Color": "Gris"},
            {"ID Fase": "T2", "Parent ID Fase": "T1", "Número de Fase": "Proyecto Alfa", "Nombre de Tarea": "Frontend", "Depende de (ID Fase)": None, "Duración (días)": 3, "Fecha de Inicio (solo si independiente)": hoy, "Horas Invertidas": 40, "Responsable(s)": "Carlos M.", "Notas Extra": "", "Color": "Azul"},
            {"ID Fase": "T3", "Parent ID Fase": "T1", "Número de Fase": "Proyecto Alfa", "Nombre de Tarea": "Backend", "Depende de (ID Fase)": "T2", "Duración (días)": 4, "Fecha de Inicio (solo si independiente)": None, "Horas Invertidas": 35, "Responsable(s)": "Ana P.", "Notas Extra": "", "Color": "Rojo"},
            {"ID Fase": "T4", "Parent ID Fase": None, "Número de Fase": "Proyecto Beta", "Nombre de Tarea": "Lanzamiento", "Depende de (ID Fase)": None, "Duración (días)": 5, "Fecha de Inicio (solo si independiente)": hoy, "Horas Invertidas": 15, "Responsable(s)": "Dirección", "Notas Extra": "", "Color": "Verde"},
        ])
    else:
        for col in ["Notas Extra", "Parent ID Fase", "Responsable(s)"]:
            if col not in df.columns: df[col] = ""
            
        if "Horas Invertidas" not in df.columns: df["Horas Invertidas"] = 0
        if "Color" not in df.columns:
            df["Color"] = "Por defecto"
        else:
            df["Color"] = df["Color"].apply(lambda x: x if x in opciones_color else "Por defecto")
            
        for col in ["ID Fase", "Parent ID Fase", "Número de Fase", "Nombre de Tarea", "Responsable(s)", "Notas Extra", "Depende de (ID Fase)"]:
            if col in df.columns:
                df[col] = df[col].astype(str).replace(["nan", "None", "NaN"], None)
                
        if "Duración (días)" in df.columns:
            df["Duración (días)"] = pd.to_numeric(df["Duración (días)"], errors='coerce').fillna(1).astype(int)
            
        if "Horas Invertidas" in df.columns:
            df["Horas Invertidas"] = pd.to_numeric(df["Horas Invertidas"], errors='coerce').fillna(0)
            
        if "Fecha de Inicio (solo si independiente)" in df.columns:
            df["Fecha de Inicio (solo si independiente)"] = pd.to_datetime(df["Fecha de Inicio (solo si independiente)"], errors='coerce').dt.date
            
        st.session_state['tasks'] = df

except Exception as e:
    st.error(f"Error de conexión con Google Sheets: {e}")
    st.stop()

st.write("### 1. Edita el Calendario de Proyectos")

# 3. Editor de Datos PRINCIPAL
orden_columnas = [
    "ID Fase", 
    "Parent ID Fase", 
    "Número de Fase", 
    "Nombre de Tarea", 
    "Depende de (ID Fase)", 
    "Duración (días)", 
    "Fecha de Inicio (solo si independiente)",
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
        "ID Fase": st.column_config.TextColumn("ID Fase", required=True),
        "Parent ID Fase": st.column_config.TextColumn("Parent ID Fase (Padre)"),
        "Número de Fase": st.column_config.TextColumn("Número de Fase", required=True), 
        "Nombre de Tarea": st.column_config.TextColumn("Nombre de Tarea", required=True),
        "Depende de (ID Fase)": st.column_config.TextColumn("Depende de (ID Fase) (ID Fase)"),
        "Duración (días)": st.column_config.NumberColumn("Duración (días)", min_value=1, step=1, required=True),
        "Fecha de Inicio (solo si independiente)": st.column_config.DateColumn("Fecha de Inicio (solo si independiente) (if independent)", format="YYYY-MM-DD"),
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

if st.button("💾 Guardar Cambios en Google Sheets"):
    try:
        conn.update(spreadsheet=SHEET_URL, worksheet=TAB_NAME, data=edited_df)
        st.success("¡Base de datos actualizada con éxito!")
        st.cache_data.clear() 
    except Exception as e:
        st.error(f"Error al guardar: {e}")

calculated_data = {}

try:
    # === PRIMERA PASADA: Cálculos Base ===
    for index, row in edited_df.iterrows():
        if pd.isna(row["ID Fase"]) or str(row["ID Fase"]).strip() in ["None", ""]:
            continue
            
        t_id = str(row["ID Fase"]).strip()
        t_parent_raw = row.get("Parent ID Fase")
        t_parent = str(t_parent_raw).strip() if pd.notna(t_parent_raw) and str(t_parent_raw) not in ["None", "nan", "NaN", ""] else None
        
        t_project = str(row["Número de Fase"]).strip() if pd.notna(row["Número de Fase"]) and str(row["Número de Fase"]) != "None" else "Sin Proyecto"
        t_task = str(row["Nombre de Tarea"]).strip()
        t_resp = str(row.get("Responsable(s)", "")).strip() if pd.notna(row.get("Responsable(s)")) else ""
        t_horas = float(row.get("Horas Invertidas", 0))
        t_notas = str(row.get("Notas Extra", "")).strip() if pd.notna(row.get("Notas Extra")) else ""
        t_color_raw = str(row.get("Color", "Por defecto")).strip()
        
        t_pre_raw = row["Depende de (ID Fase)"]
        t_pre = str(t_pre_raw).strip() if pd.notna(t_pre_raw) and str(t_pre_raw) not in ["None", "nan", "NaN", ""] else ""
        
        try:
            t_duration = int(row["Duración (días)"])
        except (ValueError, TypeError):
            t_duration = 1
            
        t_manual_start = pd.to_datetime(row["Fecha de Inicio (solo si independiente)"]) if pd.notna(row["Fecha de Inicio (solo si independiente)"]) and row["Fecha de Inicio (solo si independiente)"] != "" else None
        
        if t_pre == "":
            dependency_text = "Independiente 🟢"
            t_start = t_manual_start if t_manual_start is not None else default_start
        else:
            dependency_text = f"Depende de: {t_pre} 🔗"
            if t_pre in calculated_data:
                earliest_start = calculated_data[t_pre]["Original_Finish"] 
            else:
                earliest_start = default_start 
            
            t_start = t_manual_start if t_manual_start is not None and t_manual_start > earliest_start else earliest_start
        
        t_start = pd.to_datetime(t_start)
        t_end = t_start + pd.Timedelta(days=t_duration)
        
        calculated_data[t_id] = {
            "ID Fase": t_id,
            "Parent ID Fase": t_parent,
            "Número de Fase": t_project,
            "Nombre de Tarea": t_task,
            "Responsable(s)": t_resp,
            "Horas Invertidas": t_horas,
            "Notas Extra": t_notas,
            "Color_Raw": t_color_raw, 
            "Original_Start": t_start,
            "Original_Finish": t_end,
            "Duration": t_duration,
            "Depends_On_ID": t_pre, 
            "Dependency Info": dependency_text
        }

    # === SEGUNDA PASADA: Ajustar las Tareas Padre ===
    padres_ids = set([data["Parent ID Fase"] for t_id, data in calculated_data.items() if data["Parent ID Fase"]])
    
    for p_id in padres_ids:
        if p_id in calculated_data:
            hijos = [data for t_id, data in calculated_data.items() if data["Parent ID Fase"] == p_id]
            if hijos:
                min_start = min([h["Original_Start"] for h in hijos])
                max_finish = max([h["Original_Finish"] for h in hijos])
                
                calculated_data[p_id]["Original_Start"] = min_start
                calculated_data[p_id]["Original_Finish"] = max_finish
                calculated_data[p_id]["Duration"] = (max_finish - min_start).days
                calculated_data[p_id]["Dependency Info"] = "Tarea Padre 📂"
                calculated_data[p_id]["Horas Invertidas"] = sum([h["Horas Invertidas"] for h in hijos])
                
                if not calculated_data[p_id]["Responsable(s)"]:
                    resps = set([h["Responsable(s)"] for h in hijos if h["Responsable(s)"]])
                    calculated_data[p_id]["Responsable(s)"] = ", ".join(resps)

    # === TERCERA PASADA: Cadenas Visuales (Rutas de Dependencia) ===
    def get_root_task(task_id, visited=None):
        if visited is None: visited = set()
        if task_id in visited: return task_id 
        visited.add(task_id)
        
        if task_id not in calculated_data:
            return task_id
            
        pred_id = calculated_data[task_id].get("Depends_On_ID", "")
        if not pred_id or pred_id not in calculated_data:
            return task_id
            
        if calculated_data[task_id]["Parent ID Fase"] != calculated_data[pred_id]["Parent ID Fase"]:
            return task_id
            
        return get_root_task(pred_id, visited)

    for tid, data in calculated_data.items():
        if data["Parent ID Fase"]: 
            root_id = get_root_task(tid)
            calculated_data[tid]["Root_ID"] = root_id
            
            if root_id in calculated_data:
                root_name = calculated_data[root_id]["Nombre de Tarea"]
                calculated_data[tid]["Track_Name"] = f"   ↳ Ruta: {root_name}"
            else:
                calculated_data[tid]["Track_Name"] = f"   ↳ Subtareas"

    # Formatear para graficar
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
        # === CREAR ESPACIO VISUAL ENTRE TAREAS SECUENCIALES ===
        def adjust_finish_for_plot(row):
            if row["Finish"] == row["Original_Finish"]:
                return row["Finish"] - pd.Timedelta(hours=3)
            return row["Finish"]
            
        final_df["Plot_Finish"] = final_df.apply(adjust_finish_for_plot, axis=1)
        
        def get_sort_key(row_data):
            p_id = row_data["Parent ID Fase"]
            t_id = row_data["ID Fase"]
            
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
        final_df = final_df.sort_values(by=["Número de Fase", "Sort_Key", "Original_Start"])
        
        def get_y_axis_name(row_data):
            p_id = row_data["Parent ID Fase"]
            t_id = row_data["ID Fase"]
            
            if p_id and p_id in calculated_data:
                return row_data.get("Track_Name", f"   ↳ Subtareas")
            elif t_id in padres_ids:
                return f"📂 {row_data['Nombre de Tarea']}"
            else:
                return row_data["Nombre de Tarea"]

        final_df["Llave_Secreta"] = final_df["Número de Fase"].astype(str) + "|||" + final_df.apply(get_y_axis_name, axis=1)
        
        final_df["Orig_Start_str"] = final_df["Original_Start"].dt.strftime('%d %b')
        final_df["Orig_Finish_str"] = final_df["Original_Finish"].dt.strftime('%d %b')
        
        def generar_label(x):
            if x.get("Hide_Label", False):
                return ""
                
            return (
                f"<b>{x['Número de Fase']} - {x['Nombre de Tarea']}</b><br>"
                f"{x['Orig_Start_str']} a {x['Orig_Finish_str']} - {x['Duration']} días<br>"
                f"{x['Horas Invertidas']} hrs<br>"
                f"{x['Responsable(s)']}"
            )

        final_df["Label"] = final_df.apply(generar_label, axis=1)
        
        final_df["Color_Key"] = final_df.apply(
            lambda row: f"{row['ID Fase']} (Completado)" if row["Status"] == "Pasado" else row["ID Fase"], 
            axis=1
        )
        
        color_map = {} 
        pastel_colors = px.colors.qualitative.Pastel
        color_idx = 0
        
        project_default_colors = {}
        for p in final_df["Número de Fase"].unique():
            project_default_colors[p] = pastel_colors[color_idx % len(pastel_colors)]
            color_idx += 1
            
        for index, row in final_df.iterrows():
            tid = row["ID Fase"]
            active_key = tid
            past_key = f"{tid} (Completado)"
            
            if active_key not in color_map:
                user_color = str(row.get("Color_Raw", "Por defecto")).strip()
                
                if user_color != "Por defecto" and user_color in COLOR_MAP_ESP:
                    base_color = COLOR_MAP_ESP[user_color]
                else:
                    base_color = project_default_colors.get(row["Número de Fase"], "#3366cc")
                    
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
        # === CÁLCULOS DEL RESUMEN ===
        fecha_inicio_global = final_df["Original_Start"].min()
        fecha_fin_global = final_df["Original_Finish"].max()
        
        dias_totales = (fecha_fin_global - fecha_inicio_global).days
        dias_restantes = max(0, (fecha_fin_global.date() - hoy).days)
        tareas_unicas = len([t for t, d in calculated_data.items() if t not in padres_ids])
        total_horas = sum([d["Horas Invertidas"] for t, d in calculated_data.items() if t not in padres_ids])
        
        # Cálculos de Tareas y Proyectos Activos
        tareas_activas = 0
        proyectos_stats = {}
        
        for t_id, data in calculated_data.items():
            o_start = data["Original_Start"].date()
            o_finish = data["Original_Finish"].date()
            
            # Contar tareas activas (solo tareas hijas directas)
            if t_id not in padres_ids:
                if o_start <= hoy < o_finish:
                    tareas_activas += 1
                    
            # Registrar inicios y fines de cada proyecto
            proj = data["Número de Fase"]
            if proj not in proyectos_stats:
                proyectos_stats[proj] = {"inicio": o_start, "fin": o_finish}
            else:
                if o_start < proyectos_stats[proj]["inicio"]: proyectos_stats[proj]["inicio"] = o_start
                if o_finish > proyectos_stats[proj]["fin"]: proyectos_stats[proj]["fin"] = o_finish
                
        # Contar cuántos proyectos están en su ventana de tiempo activa
        proyectos_activos = sum(1 for p, dates in proyectos_stats.items() if dates["inicio"] <= hoy < dates["fin"])

        # === DIBUJAR MÉTRICAS EN 6 COLUMNAS ===
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("⏳ Duración Total", f"{dias_totales} días")
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
                "Número de Fase": True,
                "Parent ID Fase": True,
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
                
        # === LÓGICA DE HITOS (MILESTONES) ===
        hitos_unicos = set()
        
        fechas_fin_proy = {}
        for idx, row in final_df.iterrows():
            p = row["Número de Fase"]
            f = row["Original_Finish"]
            t = row["Llave_Secreta"].split("|||")[1] 
            if p not in fechas_fin_proy or f > fechas_fin_proy[p]["fecha"]:
                fechas_fin_proy[p] = {"fecha": f, "tarea": t}
                
        for p, datos in fechas_fin_proy.items():
            hitos_unicos.add((p, datos["tarea"], datos["fecha"]))
            
        for idx, row in final_df.iterrows():
            if "Independiente" in row["Dependency Info"] and row["ID Fase"] not in padres_ids:
                hitos_unicos.add((row["Número de Fase"], row["Llave_Secreta"].split("|||")[1], row["Original_Finish"]))
                
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
            marker=dict(symbol='diamond', size=16, color='#D30000', line=dict(color='black', width=1.5)),
            text=["Fin"] * len(hitos_x),
            textposition="middle right",
            textfont=dict(color="black", size=10, family="Arial"),
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
    
    # === TABLA DE REPORTES ===
    st.write("### 📋 Reporte Final Descargable")
    with st.expander("Haz clic aquí para ver y descargar el reporte completo", expanded=True):
        
        table_data = []
        for t_id, data in calculated_data.items():
            o_start = data["Original_Start"]
            o_finish = data["Original_Finish"]
            
            if o_finish.date() <= hoy:
                status = "Completado ✅"
            elif o_start.date() > hoy:
                status = "Pendiente ⏳"
            else:
                status = "En Proceso 🔵"
                
            table_data.append({
                "ID": t_id,
                "Parent ID Fase": data["Parent ID Fase"] if data["Parent ID Fase"] else "-",
                "Proyecto": data["Número de Fase"],
                "Tarea": data["Nombre de Tarea"],
                "Responsable(s)": data["Responsable(s)"],
                "Horas": data["Horas Invertidas"],
                "Inicio": o_start.strftime("%d/%m/%Y"),
                "Fin": o_finish.strftime("%d/%m/%Y"),
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
    st.error(f"**Error de Dependencia:** La tarea de la que dependes no se calculó bien o le falta información. Detalles: {e}")
except Exception as e:
    st.error(f"Hubo un problema procesando los datos. Detalles técnicos: {e}")
