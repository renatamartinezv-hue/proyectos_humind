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
            {"Task ID": "T1", "Parent Task ID": None, "Project Name": "Proyecto Alfa", "Task Name": "Fase de Desarrollo", "Responsable(s)": "Equipo Tech", "Horas Invertidas": 0, "Color": "Gris", "Duration (Days)": 1, "Depends On": None, "Start Date": hoy, "Notas Extra": ""},
            {"Task ID": "T2", "Parent Task ID": "T1", "Project Name": "Proyecto Alfa", "Task Name": "Frontend", "Responsable(s)": "Carlos M.", "Horas Invertidas": 40, "Color": "Azul", "Duration (Days)": 3, "Depends On": None, "Start Date": hoy, "Notas Extra": ""},
            {"Task ID": "T3", "Parent Task ID": "T1", "Project Name": "Proyecto Alfa", "Task Name": "Backend", "Responsable(s)": "Ana P.", "Horas Invertidas": 35, "Color": "Rojo", "Duration (Days)": 4, "Depends On": "T2", "Start Date": None, "Notas Extra": ""},
            {"Task ID": "T4", "Parent Task ID": None, "Project Name": "Proyecto Beta", "Task Name": "Lanzamiento", "Responsable(s)": "Dirección", "Horas Invertidas": 15, "Color": "Verde", "Duration (Days)": 5, "Depends On": None, "Start Date": hoy, "Notas Extra": ""},
        ])
    else:
        for col in ["Notas Extra", "Parent Task ID", "Responsable(s)"]:
            if col not in df.columns: df[col] = ""
            
        if "Horas Invertidas" not in df.columns: df["Horas Invertidas"] = 0
        if "Color" not in df.columns:
            df["Color"] = "Por defecto"
        else:
            df["Color"] = df["Color"].apply(lambda x: x if x in opciones_color else "Por defecto")
            
        for col in ["Task ID", "Parent Task ID", "Project Name", "Task Name", "Responsable(s)", "Notas Extra", "Depends On"]:
            if col in df.columns:
                df[col] = df[col].astype(str).replace(["nan", "None", "NaN"], None)
                
        if "Duration (Days)" in df.columns:
            df["Duration (Days)"] = pd.to_numeric(df["Duration (Days)"], errors='coerce').fillna(1).astype(int)
            
        if "Horas Invertidas" in df.columns:
            df["Horas Invertidas"] = pd.to_numeric(df["Horas Invertidas"], errors='coerce').fillna(0)
            
        if "Start Date" in df.columns:
            df["Start Date"] = pd.to_datetime(df["Start Date"], errors='coerce').dt.date
            
        if "Description" in df.columns:
            df = df.drop(columns=["Description"])
            
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
    "Responsable(s)",
    "Horas Invertidas",
    "Notas Extra", 
    "Color", 
    "Duration (Days)", 
    "Depends On", 
    "Start Date"
]

edited_df = st.data_editor(
    st.session_state['tasks'], 
    num_rows="dynamic", 
    width="stretch",
    column_order=orden_columnas, 
    column_config={
        "Task ID": st.column_config.TextColumn("Task ID", required=True),
        "Parent Task ID": st.column_config.TextColumn("Parent Task ID", help="Deja vacío si es tarea principal."),
        "Project Name": st.column_config.TextColumn("Project Name", required=True), 
        "Task Name": st.column_config.TextColumn("Task Name", required=True),
        "Responsable(s)": st.column_config.TextColumn("Responsable(s)"),
        "Horas Invertidas": st.column_config.NumberColumn("Horas Invertidas", min_value=0),
        "Notas Extra": st.column_config.TextColumn("📝 Notas Extra"), 
        "Color": st.column_config.SelectboxColumn(
            "Color de Tarea", 
            options=opciones_color,
            default="Por defecto",
            required=True
        ),
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
    # 4. Cálculo Matemático
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
        
        try:
            t_duration = int(row["Duration (Days)"])
        except (ValueError, TypeError):
            t_duration = 1
            
        t_manual_start = pd.to_datetime(row["Start Date"]) if pd.notna(row["Start Date"]) and row["Start Date"] != "" else None
        
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
            "Task ID": t_id,
            "Parent Task ID": t_parent,
            "Project": t_project,
            "Task": t_task,
            "Responsable(s)": t_resp,
            "Horas Invertidas": t_horas,
            "Notas Extra": t_notas,
            "Color_Raw": t_color_raw, 
            "Original_Start": t_start,
            "Original_Finish": t_end,
            "Duration": t_duration,
            "Dependency Info": dependency_text
        }

    # === SEGUNDA PASADA: Ajustar las Tareas Padre ===
    padres_ids = set([data["Parent Task ID"] for t_id, data in calculated_data.items() if data["Parent Task ID"]])
    
    for p_id in padres_ids:
        if p_id in calculated_data:
            hijos = [data for t_id, data in calculated_data.items() if data["Parent Task ID"] == p_id]
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

    # Formatear para graficar
    final_tasks = []
    fecha_hoy_segura = pd.to_datetime(hoy)
    
    for t_id, data in calculated_data.items():
        o_start = data["Original_Start"]
        o_finish = data["Original_Finish"]
        
        if o_start.date() < hoy and o_finish.date() > hoy:
            final_tasks.append({**data, "Start": o_start, "Finish": fecha_hoy_segura, "Status": "Pasado"})
            final_tasks.append({**data, "Start": fecha_hoy_segura, "Finish": o_finish, "Status": "Activo"})
        elif o_finish.date() <= hoy:
            final_tasks.append({**data, "Start": o_start, "Finish": o_finish, "Status": "Pasado"})
        else:
            final_tasks.append({**data, "Start": o_start, "Finish": o_finish, "Status": "Activo"})
            
    final_df = pd.DataFrame(final_tasks)
    
    if not final_df.empty:
        
        # === ORDENAMIENTO PERFECTO (Padre primero, luego sus hijos) ===
        def get_sort_key(row_data):
            p_id = row_data["Parent Task ID"]
            t_id = row_data["Task ID"]
            
            if p_id and p_id in calculated_data:
                # Es hijo -> Agrupado bajo el tiempo del padre, con sufijo _1_ para ir debajo
                parent_start = calculated_data[p_id]["Original_Start"].timestamp()
                return f"{parent_start}_1_{p_id}" 
            elif t_id in padres_ids:
                # Es padre -> Prefijo _0_ para ir arriba
                return f"{row_data['Original_Start'].timestamp()}_0_{t_id}"
            else:
                # Independiente
                return f"{row_data['Original_Start'].timestamp()}_0_{t_id}"

        final_df["Sort_Key"] = final_df.apply(get_sort_key, axis=1)
        final_df = final_df.sort_values(by=["Project", "Sort_Key", "Original_Start"])
        
        # === ASIGNAR ETIQUETAS Y RENGLONES EJE Y ===
        def get_y_axis_name(row_data):
            p_id = row_data["Parent Task ID"]
            t_id = row_data["Task ID"]
            
            if p_id and p_id in calculated_data:
                nombre_padre = calculated_data[p_id]["Task"]
                return f"   ↳ Subtareas de {nombre_padre}"
            elif t_id in padres_ids:
                return f"📂 {row_data['Task']}"
            else:
                return row_data["Task"]

        # Cada Padre tiene su renglón, y los Hijos comparten el suyo debajo del Padre
        final_df["Llave_Secreta"] = final_df["Project"].astype(str) + "|||" + final_df.apply(get_y_axis_name, axis=1)
        
        final_df["Orig_Start_str"] = final_df["Original_Start"].dt.strftime('%d %b')
        final_df["Orig_Finish_str"] = final_df["Original_Finish"].dt.strftime('%d %b')
        
        # Texto de 4 renglones 
        def generar_label(x):
            return (
                f"<b>{x['Project']} - {x['Task']}</b><br>"
                f"{x['Orig_Start_str']} a {x['Orig_Finish_str']} - {x['Duration']} días<br>"
                f"{x['Horas Invertidas']} hrs<br>"
                f"{x['Responsable(s)']}"
            )

        final_df["Label"] = final_df.apply(generar_label, axis=1)
        
        final_df["Color_Key"] = final_df.apply(
            lambda row: f"{row['Task ID']} (Completado)" if row["Status"] == "Pasado" else row["Task ID"], 
            axis=1
        )
        
        color_map = {} 
        pastel_colors = px.colors.qualitative.Pastel
        color_idx = 0
        
        project_default_colors = {}
        for p in final_df["Project"].unique():
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
                    base_color = project_default_colors.get(row["Project"], "#3366cc")
                    
                color_map[active_key] = base_color
                
                # LÓGICA DE TRANSPARENCIA: Mismo color exacto, pero al 30% de opacidad para tareas pasadas
                c_str = str(base_color).strip().lower()
                try:
                    if c_str.startswith('#'):
                        hex_c = c_str.lstrip('#')
                        if len(hex_c) == 3: hex_c = "".join([c*2 for c in hex_c])
                        r, g, b = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
                    else:
                        r, g, b = 150, 150, 150
                        
                    # 0.3 es el nivel de transparencia (30%). Se verá como un color pastel idéntico al original.
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
        tareas_unicas = final_df["Task"].nunique()
        total_horas = final_df[final_df["Task ID"].apply(lambda x: x not in padres_ids)]["Horas Invertidas"].sum()
        
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
            x_end="Finish", 
            y="Llave_Secreta", 
            color="Color_Key", 
            color_discrete_map=color_map, 
            text="Label",     
            hover_data={
                "Color_Key": False,
                "Llave_Secreta": False,
                "Project": True,
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
                # Ahora la llave secreta tiene el nombre correcto del eje Y en la posición 1
                tareas = [str(val).split("|||")[1] for val in trace.y]
                trace.y = [proyectos, tareas] 
                
        # === LÓGICA DE HITOS (MILESTONES) ===
        hitos_unicos = set()
        
        fechas_fin_proy = {}
        for idx, row in final_df.iterrows():
            p = row["Project"]
            f = row["Original_Finish"]
            t = row["Llave_Secreta"].split("|||")[1] # Usamos el nombre exacto del renglón visual
            if p not in fechas_fin_proy or f > fechas_fin_proy[p]["fecha"]:
                fechas_fin_proy[p] = {"fecha": f, "tarea": t}
                
        for p, datos in fechas_fin_proy.items():
            hitos_unicos.add((p, datos["tarea"], datos["fecha"]))
            
        for idx, row in final_df.iterrows():
            if "Independiente" in row["Dependency Info"] and row["Task ID"] not in padres_ids:
                hitos_unicos.add((row["Project"], row["Llave_Secreta"].split("|||")[1], row["Original_Finish"]))
                
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
            tickformat="%b %d, %Y"
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
                "Parent Task ID": data["Parent Task ID"] if data["Parent Task ID"] else "-",
                "Proyecto": data["Project"],
                "Tarea": data["Task"],
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
