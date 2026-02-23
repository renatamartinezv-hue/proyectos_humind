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
            {"ID Tarea": "T1", "ID Tarea Padre": None, "Nombre del Proyecto": "Proyecto Alfa", "Nombre de la Tarea": "Fase de Desarrollo", "Depende de (ID)": None, "Duración (Días)": 1, "Fecha de Inicio": hoy, "Horas Invertidas": 0, "Responsable(s)": "Equipo Tech", "Notas Extra": "", "Color de Tarea": "Gris"},
            {"ID Tarea": "T2", "ID Tarea Padre": "T1", "Nombre del Proyecto": "Proyecto Alfa", "Nombre de la Tarea": "Frontend", "Depende de (ID)": None, "Duración (Días)": 3, "Fecha de Inicio": hoy, "Horas Invertidas": 40, "Responsable(s)": "Carlos M.", "Notas Extra": "", "Color de Tarea": "Azul"},
            {"ID Tarea": "T3", "ID Tarea Padre": "T1", "Nombre del Proyecto": "Proyecto Alfa", "Nombre de la Tarea": "Backend", "Depende de (ID)": "T2", "Duración (Días)": 4, "Fecha de Inicio": None, "Horas Invertidas": 35, "Responsable(s)": "Ana P.", "Notas Extra": "", "Color de Tarea": "Rojo"},
            {"ID Tarea": "T4", "ID Tarea Padre": None, "Nombre del Proyecto": "Proyecto Beta", "Nombre de la Tarea": "Lanzamiento", "Depende de (ID)": None, "Duración (Días)": 5, "Fecha de Inicio": hoy, "Horas Invertidas": 15, "Responsable(s)": "Dirección", "Notas Extra": "", "Color de Tarea": "Verde"},
        ])
    else:
        for col in ["Notas Extra", "ID Tarea Padre", "Responsable(s)"]:
            if col not in df.columns: df[col] = ""
            
        if "Horas Invertidas" not in df.columns: df["Horas Invertidas"] = 0
        if "Color de Tarea" not in df.columns:
            df["Color de Tarea"] = "Por defecto"
        else:
            df["Color de Tarea"] = df["Color de Tarea"].apply(lambda x: x if x in opciones_color else "Por defecto")
            
        for col in ["ID Tarea", "ID Tarea Padre", "Nombre del Proyecto", "Nombre de la Tarea", "Responsable(s)", "Notas Extra", "Depende de (ID)"]:
            if col in df.columns:
                df[col] = df[col].astype(str).replace(["nan", "None", "NaN"], None)
                
        if "Duración (Días)" in df.columns:
            df["Duración (Días)"] = pd.to_numeric(df["Duración (Días)"], errors='coerce').fillna(1).astype(int)
            
        if "Horas Invertidas" in df.columns:
            df["Horas Invertidas"] = pd.to_numeric(df["Horas Invertidas"], errors='coerce').fillna(0)
            
        if "Fecha de Inicio" in df.columns:
            df["Fecha de Inicio"] = pd.to_datetime(df["Fecha de Inicio"], errors='coerce').dt.date
            
        st.session_state['tasks'] = df

except Exception as e:
    st.error(f"Error de conexión con Google Sheets: {e}")
    st.stop()

st.write("### 1. Edita el Calendario de Proyectos")

# 3. Editor de Datos PRINCIPAL
orden_columnas = [
    "ID Tarea", 
    "ID Tarea Padre", 
    "Nombre del Proyecto", 
    "Nombre de la Tarea", 
    "Depende de (ID)", 
    "Duración (Días)", 
    "Fecha de Inicio",
    "Horas Invertidas",
    "Responsable(s)",
    "Notas Extra", 
    "Color de Tarea" 
]

edited_df = st.data_editor(
    st.session_state['tasks'], 
    num_rows="dynamic", 
    width="stretch",
    column_order=orden_columnas, 
    column_config={
        "ID Tarea": st.column_config.TextColumn("ID Tarea", required=True),
        "ID Tarea Padre": st.column_config.TextColumn("ID Tarea Padre", help="Deja vacío si es tarea principal."),
        "Nombre del Proyecto": st.column_config.TextColumn("Nombre del Proyecto", required=True), 
        "Nombre de la Tarea": st.column_config.TextColumn("Nombre de la Tarea", required=True),
        "Depende de (ID)": st.column_config.TextColumn("Depende de (ID)"),
        "Duración (Días)": st.column_config.NumberColumn("Duración (Días)", min_value=1, step=1, required=True),
        "Fecha de Inicio": st.column_config.DateColumn("Fecha de Inicio (Si es indep.)", format="YYYY-MM-DD"),
        "Horas Invertidas": st.column_config.NumberColumn("Horas Invertidas", min_value=0),
        "Responsable(s)": st.column_config.TextColumn("Responsable(s)"),
        "Notas Extra": st.column_config.TextColumn("📝 Notas Extra"), 
        "Color de Tarea": st.column_config.SelectboxColumn(
            "Color de Tarea", 
            options=opciones_color,
            default="Por defecto",
            required=True
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
        if pd.isna(row["ID Tarea"]) or str(row["ID Tarea"]).strip() in ["None", ""]:
            continue
            
        t_id = str(row["ID Tarea"]).strip()
        t_parent_raw = row.get("ID Tarea Padre")
        t_parent = str(t_parent_raw).strip() if pd.notna(t_parent_raw) and str(t_parent_raw) not in ["None", "nan", "NaN", ""] else None
        
        t_project = str(row["Nombre del Proyecto"]).strip() if pd.notna(row["Nombre del Proyecto"]) and str(row["Nombre del Proyecto"]) != "None" else "Sin Proyecto"
        t_task = str(row["Nombre de la Tarea"]).strip()
        t_resp = str(row.get("Responsable(s)", "")).strip() if pd.notna(row.get("Responsable(s)")) else ""
        t_horas = float(row.get("Horas Invertidas", 0))
        t_notas = str(row.get("Notas Extra", "")).strip() if pd.notna(row.get("Notas Extra")) else ""
        t_color_raw = str(row.get("Color de Tarea", "Por defecto")).strip()
        
        t_pre_raw = row["Depende de (ID)"]
        t_pre = str(t_pre_raw).strip() if pd.notna(t_pre_raw) and str(t_pre_raw) not in ["None", "nan", "NaN", ""] else ""
        
        try:
            t_duration = int(row["Duración (Días)"])
        except (ValueError, TypeError):
            t_duration = 1
            
        t_manual_start = pd.to_datetime(row["Fecha de Inicio"]) if pd.notna(row["Fecha de Inicio"]) and row["Fecha de Inicio"] != "" else None
        
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
            "ID Tarea": t_id,
            "ID Tarea Padre": t_parent,
            "Proyecto": t_project,
            "Tarea": t_task,
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
    padres_ids = set([data["ID Tarea Padre"] for t_id, data in calculated_data.items() if data["ID Tarea Padre"]])
    
    for p_id in padres_ids:
        if p_id in calculated_data:
            hijos = [data for t_id, data in calculated_data.items() if data["ID Tarea Padre"] == p_id]
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
            
        if calculated_data[task_id]["ID Tarea Padre"] != calculated_data[pred_id]["ID Tarea Padre"]:
            return task_id
            
        return get_root_task(pred_id, visited)

    for tid, data in calculated_data.items():
        if data["ID Tarea Padre"]: 
            root_id = get_root_task(tid)
            calculated_data[tid]["Root_ID"] = root_id
            
            if root_id in calculated_data:
                root_name = calculated_data[root_id]["Tarea"]
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
            p_id = row_data["ID Tarea Padre"]
            t_id = row_data["ID Tarea"]
            
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
        final_df = final_df.sort_values(by=["Proyecto", "Sort_Key", "Original_Start"])
        
        def get_y_axis_name(row_data):
            p_id = row_data["ID Tarea Padre"]
            t_id = row_data["ID Tarea"]
            
            if p_id and p_id in calculated_data:
                return row_data.get("Track_Name", f"   ↳ Subtareas")
            elif t_id in padres_ids:
                return f"📂 {row_data['Tarea']}"
            else:
                return row_data["Tarea"]

        final_df["Llave_Secreta"] = final_df["Proyecto"].astype(str) + "|||" + final_df.apply(get_y_axis_name, axis=1)
        
        final_df["Orig_Start_str"] = final_df["Original_Start"].dt.strftime('%d %b')
        final_df["Orig_Finish_str"] = final_df["Original_Finish"].dt.strftime('%d %b')
        
        def generar_label(x):
            if x.get("Hide_Label", False):
                return ""
                
            return (
                f"<b>{x['Proyecto']} - {x['Tarea']}</b><br>"
                f"{x['Orig_Start_str']} a {x['Orig_Finish_str']} - {x['Duration']} días<br>"
                f"{x['Horas Invertidas']} hrs<br>"
                f"{x['Responsable(s)']}"
            )

        final_df["Label"] = final_df.apply(generar_label, axis=1)
        
        final_df["Color_Key"] = final_df.apply(
            lambda row: f"{row['ID Tarea']} (Completado)" if row["Status"] == "Pasado" else row["ID Tarea"], 
            axis=1
        )
        
        color_map = {} 
        pastel_colors = px.colors.qualitative.Pastel
        color_idx = 0
        
        project_default_colors = {}
        for p in final_df["Proyecto"].unique():
            project_default_colors[p] = pastel_colors[color_idx % len(pastel_colors)]
            color_idx += 1
            
        for index, row in final_df.iterrows():
            tid = row["ID Tarea"]
            active_key = tid
            past_key = f"{tid} (Completado)"
            
            if active_key not in color_map:
                user_color = str(row.get("Color_Raw", "Por defecto")).strip()
                
                if user_color != "Por defecto" and user_color in COLOR_MAP_ESP:
                    base_color = COLOR_MAP_ESP[user_color]
                else:
                    base_color = project_default_colors.get(row["Proyecto"], "#3366cc")
                    
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
        tareas_unicas = final_df["Tarea"].nunique()
        total_horas = final_df[final_df["ID Tarea"].apply(lambda x: x not in padres_ids)]["Horas Invertidas"].sum()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("⏳ Duración Total", f"{dias_totales} días")
        col2.metric("📅 Días Restantes", f"{dias_restantes} días")
        col3.metric("📝 Total de Tareas", tareas_unicas)
        col4.metric("⏱️ Horas Totales", f"{total_horas} hrs")

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
                "Proyecto": True,
                "ID Tarea Padre": True,
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
            p = row["Proyecto"]
            f = row["Original_Finish"]
            t = row["Llave_Secreta"].split("|||")[1] 
            if p not in fechas_fin_proy or f > fechas_fin_proy[p]["fecha"]:
                fechas_fin_proy[p] = {"fecha": f, "tarea": t}
                
        for p, datos in fechas_fin_proy.items():
            hitos_unicos.add((p, datos["tarea"], datos["fecha"]))
            
        for idx, row in final_df.iterrows():
            if "Independiente" in row["Dependency Info"] and row["ID Tarea"] not in padres_ids:
                hitos_unicos.add((row["Proyecto"], row["Llave_Secreta"].split("|||")[1], row["Original_Finish"]))
                
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
                "ID Tarea Padre": data["ID Tarea Padre"] if data["ID Tarea Padre"] else "-",
                "Proyecto": data["Proyecto"],
                "Tarea": data["Tarea"],
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
    st.error(f"**Error de Dependencia:** La tarea de la que dependes no se calculó bien. Detalles: {e}")
except Exception as e:
    st.error(f"Hubo un problema procesando los datos. Detalles técnicos: {e}")
