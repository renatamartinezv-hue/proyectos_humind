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
            {"Task ID": "T1", "Project Name": "Proyecto 1", "Task Name": "Project Kickoff", "Description": "Reunión inicial", "Color": "Rojo", "Duration (Days)": 2, "Depends On": None, "Start Date": hoy, "Notas Extra": "", "Ocultar en Gráfica": False},
            {"Task ID": "T2", "Project Name": "Proyecto 1", "Task Name": "Market Research", "Description": "Análisis", "Color": "Azul", "Duration (Days)": 5, "Depends On": "T1", "Start Date": None, "Notas Extra": "", "Ocultar en Gráfica": False},
            {"Task ID": "T3", "Project Name": "Personal", "Task Name": "Comprar Café", "Description": "Para la oficina", "Color": "Por defecto", "Duration (Days)": 1, "Depends On": None, "Start Date": hoy, "Notas Extra": "Importante", "Ocultar en Gráfica": True},
        ])
    else:
        # Aseguramos que existan las nuevas columnas para evitar errores
        if "Description" not in df.columns: df["Description"] = ""
        if "Notas Extra" not in df.columns: df["Notas Extra"] = ""
        
        if "Color" not in df.columns:
            df["Color"] = "Por defecto"
        else:
            df["Color"] = df["Color"].apply(lambda x: x if x in opciones_color else "Por defecto")
            
        # Convertimos la columna de Ocultar a Booleano (True/False) de forma segura
        if "Ocultar en Gráfica" not in df.columns:
            df["Ocultar en Gráfica"] = False
        else:
            df["Ocultar en Gráfica"] = df["Ocultar en Gráfica"].map(
                lambda x: str(x).lower() in ['true', '1', 't', 'y', 'yes', 'v', 'verdadero']
            ).astype(bool)
            
        for col in ["Task ID", "Project Name", "Task Name", "Description", "Notas Extra", "Depends On"]:
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
st.info("💡 **Tip de Productividad:** Usa la tabla de aquí abajo para agregar tareas personales o apuntes. Si marcas la casilla **'👻 Ocultar en Gráfica'**, no aparecerá en el dibujo, pero sí se guardará en tu Excel descargable.")

# 3. Editor de Datos PRINCIPAL
edited_df = st.data_editor(
    st.session_state['tasks'], 
    num_rows="dynamic", 
    width="stretch",
    column_config={
        "Task ID": st.column_config.TextColumn("Task ID", required=True),
        "Project Name": st.column_config.TextColumn("Project Name", required=True), 
        "Task Name": st.column_config.TextColumn("Task Name", required=True),
        "Description": st.column_config.TextColumn("Description"), 
        "Notas Extra": st.column_config.TextColumn("📝 Notas Extra", help="Anota encargados, presupuestos o links."), 
        "Color": st.column_config.SelectboxColumn(
            "Color de Tarea", 
            options=opciones_color,
            default="Por defecto",
            required=True
        ),
        "Ocultar en Gráfica": st.column_config.CheckboxColumn(
            "👻 Ocultar en Gráfica", 
            help="Marca esta casilla para esconder la tarea del Gantt visual."
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
    # 4. Cálculo Matemático de TODAS las tareas (Visibles y Ocultas)
    for index, row in edited_df.iterrows():
        if pd.isna(row["Task ID"]) or str(row["Task ID"]).strip() in ["None", ""]:
            continue
            
        t_id = str(row["Task ID"]).strip()
        t_project = str(row["Project Name"]).strip() if pd.notna(row["Project Name"]) and str(row["Project Name"]) != "None" else "Sin Proyecto"
        t_task = str(row["Task Name"]).strip()
        t_desc = str(row.get("Description", "")).strip() if pd.notna(row.get("Description")) else ""
        t_notas = str(row.get("Notas Extra", "")).strip() if pd.notna(row.get("Notas Extra")) else ""
        t_color_raw = str(row.get("Color", "Por defecto")).strip()
        
        # Recuperamos la variable booleana
        t_ocultar = bool(row.get("Ocultar en Gráfica", False))
        
        t_pre_raw = row["Depends On"]
        t_pre = str(t_pre_raw).strip() if pd.notna(t_pre_raw) and str(t_pre_raw) != "None" else ""
        
        try:
            t_duration = int(row["Duration (Days)"])
        except (ValueError, TypeError):
            t_duration = 1
            
        t_manual_start = pd.to_datetime(row["Start Date"]) if pd.notna(row["Start Date"]) and row["Start Date"] != "" else None
        
        if t_pre == "" or t_pre.lower() == "none" or t_pre == "nan":
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
            "Project": t_project,
            "Task": t_task,
            "Description": t_desc,  
            "Notas Extra": t_notas,
            "Ocultar en Gráfica": t_ocultar,
            "Color_Raw": t_color_raw, 
            "Original_Start": t_start,
            "Original_Finish": t_end,
            "Duration": t_duration,
            "Dependency Info": dependency_text
        }
        
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
        final_df = final_df.sort_values(by=["Project", "Original_Start"])
        final_df["Llave_Secreta"] = final_df["Project"].astype(str) + "|||" + final_df["Task"].astype(str)
        final_df["Orig_Start_str"] = final_df["Original_Start"].dt.strftime('%d %b')
        final_df["Orig_Finish_str"] = final_df["Original_Finish"].dt.strftime('%d %b')
        
        final_df["Label"] = final_df.apply(
            lambda x: f"{str(x['Task'])} | {str(x['Orig_Start_str'])} - {str(x['Orig_Finish_str'])}", 
            axis=1
        )
        
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
                
                c_str = str(base_color).strip().lower()
                try:
                    if c_str.startswith('#'):
                        hex_c = c_str.lstrip('#')
                        if len(hex_c) == 3: hex_c = "".join([c*2 for c in hex_c])
                        r, g, b = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
                    elif c_str.startswith('rgb'):
                        nums = c_str[c_str.find('(')+1:c_str.find(')')].split(',')
                        r, g, b = int(nums[0]), int(nums[1]), int(nums[2])
                    else:
                        r, g, b = 150, 150, 150
                        
                    r_muted = int(r * 0.4 + 210 * 0.6)
                    g_muted = int(g * 0.4 + 210 * 0.6)
                    b_muted = int(b * 0.4 + 210 * 0.6)
                    muted_color = f'rgb({r_muted},{g_muted},{b_muted})'
                except Exception:
                    muted_color = "#d3d3d3"
                
                color_map[past_key] = muted_color
    
    # === SEPARAMOS LOS DATOS: SOLO TAREAS VISIBLES PARA EL GRÁFICO ===
    if not final_df.empty:
        df_grafico = final_df[final_df["Ocultar en Gráfica"] == False].copy()
    else:
        df_grafico = pd.DataFrame()
    # =================================================================
    
    st.write("---") 
    st.write("### 📊 Resumen del Portafolio (Proyectos Visibles)")
    
    if not df_grafico.empty:
        fecha_inicio_global = df_grafico["Original_Start"].min()
        fecha_fin_global = df_grafico["Original_Finish"].max()
        
        dias_totales = (fecha_fin_global - fecha_inicio_global).days
        dias_restantes = max(0, (fecha_fin_global.date() - hoy).days)
        tareas_unicas = df_grafico["Task"].nunique()
        proyectos_activos = df_grafico[df_grafico["Original_Finish"].dt.date >= hoy]["Project"].nunique()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("⏳ Duración Total", f"{dias_totales} días")
        col2.metric("📅 Días Restantes", f"{dias_restantes} días")
        col3.metric("📝 Total de Tareas", tareas_unicas)
        col4.metric("📁 Proyectos Activos", proyectos_activos)

    st.write("### 2. Línea de Tiempo de Proyectos")
    
    if not df_grafico.empty:
        fig = px.timeline(
            df_grafico, 
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
                "Dependency Info": True
            },
        )
        
        fig.update_traces(
            textfont_size=13, 
            textfont_color="black",
            textposition='inside', 
            insidetextanchor='middle'
        )
        
        for trace in fig.data:
            if getattr(trace, "y", None) is not None:
                proyectos = [str(val).split("|||")[0] for val in trace.y]
                tareas = [str(val).split("|||")[1] for val in trace.y]
                trace.y = [proyectos, tareas] 
                
        # Milestones solo para tareas visibles
        hitos_x = []
        hitos_y_proy = []
        hitos_y_tarea = []
        
        fechas_fin_proy = {}
        for idx, row in df_grafico.iterrows():
            p = row["Project"]
            f = row["Original_Finish"]
            t = row["Task"]
            if p not in fechas_fin_proy or f > fechas_fin_proy[p]["fecha"]:
                fechas_fin_proy[p] = {"fecha": f, "tarea": t}
                
        for p, datos in fechas_fin_proy.items():
            hitos_x.append(datos["fecha"])
            hitos_y_proy.append(p)
            hitos_y_tarea.append(datos["tarea"])
            
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
        
        unique_llaves = df_grafico["Llave_Secreta"].unique()
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
            height=max(400, len(df_grafico['Task'].unique()) * 45),
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
    elif not final_df.empty:
        st.info("Todas las tareas actuales están marcadas como 'Ocultas'. Desmarca alguna arriba para ver la gráfica.")
    else:
        st.info("No hay tareas válidas para mostrar en el gráfico.")

    st.write("---")
    
    # === TABLA DE REPORTES (Muestra todo) ===
    st.write("### 📋 Reporte Final Descargable")
    with st.expander("Haz clic aquí para ver y descargar todas las tareas (Visibles y Ocultas)", expanded=True):
        
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
                
            visibilidad = "Oculta 👻" if data["Ocultar en Gráfica"] else "Visible 👁️"

            table_data.append({
                "ID": t_id,
                "Proyecto": data["Project"],
                "Tarea": data["Task"],
                "Notas Extra": data["Notas Extra"], # Columna personalizada
                "Descripción": data["Description"],
                "Inicio Calculado": o_start.strftime("%d/%m/%Y"),
                "Fin Calculado": o_finish.strftime("%d/%m/%Y"),
                "Duración": f"{data['Duration']} días",
                "Estado": status,
                "Dependencia": data["Dependency Info"].replace("🔗", "").replace("🟢", "").strip(),
                "Gráfica": visibilidad
            })
        
        df_table = pd.DataFrame(table_data)
        
        # Mostramos la tabla como dataframe de solo lectura para evitar confusiones de edición
        st.dataframe(df_table, use_container_width=True, hide_index=True)
        
        # Botón para descargar el resultado en CSV
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
