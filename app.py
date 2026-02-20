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
            {"Task ID": "T1", "Project Name": "Proyecto 1", "Task Name": "Project Kickoff", "Description": "Reunión inicial de planeación", "Duration (Days)": 2, "Depends On": None, "Start Date": hoy},
            {"Task ID": "T2", "Project Name": "Proyecto 1", "Task Name": "Market Research", "Description": "Análisis de la competencia", "Duration (Days)": 5, "Depends On": "T1", "Start Date": None},
            {"Task ID": "T3", "Project Name": "Proyecto 2", "Task Name": "Design Phase", "Description": "Bocetos y diseño conceptual", "Duration (Days)": 4, "Depends On": None, "Start Date": hoy},
        ])
    else:
        if "Description" not in df.columns:
            df["Description"] = ""
            
        for col in ["Task ID", "Project Name", "Task Name", "Description", "Depends On"]:
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
        "Description": st.column_config.TextColumn("Description"), 
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
    # 4. Cálculo Matemático de Fechas Generales
    for index, row in edited_df.iterrows():
        if pd.isna(row["Task ID"]) or str(row["Task ID"]).strip() in ["None", ""]:
            continue
            
        t_id = str(row["Task ID"]).strip()
        t_project = str(row["Project Name"]).strip() if pd.notna(row["Project Name"]) and str(row["Project Name"]) != "None" else "Sin Proyecto"
        t_task = str(row["Task Name"]).strip()
        
        t_desc_raw = row.get("Description", "")
        t_desc = str(t_desc_raw).strip() if pd.notna(t_desc_raw) and str(t_desc_raw) != "None" else ""
        
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
            "Project": t_project,
            "Task": t_task,
            "Description": t_desc,  
            "Original_Start": t_start,
            "Original_Finish": t_end,
            "Duration": t_duration,
            "Dependency Info": dependency_text
        }
        
    # === EL TRUCO MÁGICO: PARTIR LAS BARRAS ===
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
        # ES VITAL ORDENAR PRIMERO PARA QUE LA JERARQUÍA FUNCIONE
        final_df = final_df.sort_values(by=["Project", "Original_Start"])
        
        final_df["Orig_Start_str"] = final_df["Original_Start"].dt.strftime('%d %b')
        final_df["Orig_Finish_str"] = final_df["Original_Finish"].dt.strftime('%d %b')
        final_df["Label"] = final_df.apply(
            lambda x: f"{str(x['Orig_Start_str'])} - {str(x['Orig_Finish_str'])}", 
            axis=1
        )
        
        final_df["Color_Visual"] = final_df.apply(
            lambda row: f"{str(row['Project'])} (Completado)" if row["Status"] == "Pasado" else str(row["Project"]), 
            axis=1
        )
        
        color_map = {} 
        pastel_colors = px.colors.qualitative.Pastel
        color_idx = 0
        
        for p in final_df["Project"].unique():
            if p not in color_map:
                base_color = pastel_colors[color_idx % len(pastel_colors)]
                color_map[p] = base_color
                
                c_str = str(base_color).strip().lower()
                
                try:
                    if c_str.startswith('#'):
                        hex_c = c_str.lstrip('#')
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
                
                color_map[f"{p} (Completado)"] = muted_color
                color_idx += 1
    
    st.write("---") 
    st.write("### 📊 Resumen del Portafolio")
    
    if not final_df.empty:
        fecha_inicio_global = final_df["Original_Start"].min()
        fecha_fin_global = final_df["Original_Finish"].max()
        
        dias_totales = (fecha_fin_global - fecha_inicio_global).days
        dias_restantes = max(0, (fecha_fin_global.date() - hoy).days)
        tareas_unicas = final_df["Task"].nunique()
        proyectos_activos = final_df[final_df["Original_Finish"].dt.date >= hoy]["Project"].nunique()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("⏳ Duración Total", f"{dias_totales} días")
        col2.metric("📅 Días Restantes", f"{dias_restantes} días")
        col3.metric("📝 Total de Tareas", tareas_unicas)
        col4.metric("📁 Proyectos Activos", proyectos_activos)

    st.write("### 2. Línea de Tiempo de Proyectos")
    
    if not final_df.empty:
        # === AQUÍ ESTÁ LA MAGIA CORREGIDA: ÍNDICE MÚLTIPLE DE PANDAS ===
        eje_jerarquico = pd.MultiIndex.from_arrays(
            [final_df["Project"], final_df["Task"]], 
            names=["Proyecto", "Tarea"]
        )
        
        fig = px.timeline(
            final_df, 
            x_start="Start", 
            x_end="Finish", 
            y=eje_jerarquico, # Pasamos el índice estructurado, no una lista suelta
            color="Color_Visual", 
            color_discrete_map=color_map, 
            text="Label",     
            hover_data=["Dependency Info"],
        )
        # ==============================================================
        
        fig.update_traces(
            textfont_size=14, 
            textfont_color="black",
            textposition='inside', 
            insidetextanchor='middle'
        )
        
        fig.update_yaxes(
            autorange="reversed", 
            title_text="" # Eliminamos etiquetas estorbosas
        ) 
        
        fig.update_layout(
            plot_bgcolor='white', 
            height=max(400, len(final_df['Task'].unique()) * 45),
            margin=dict(l=150) 
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
        
        st.write("---")
        st.write("### 📋 Detalles del Cronograma")
        with st.expander("Haz clic aquí para desplegar la tabla con las fechas, descripciones y estados calculados"):
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
                    "Proyecto": data["Project"],
                    "Tarea": data["Task"],
                    "Descripción": data["Description"],
                    "Inicio Calculado": o_start.strftime("%d/%m/%Y"),
                    "Fin Calculado": o_finish.strftime("%d/%m/%Y"),
                    "Duración": f"{data['Duration']} días",
                    "Dependencia": data["Dependency Info"].replace("🔗", "").replace("🟢", "").strip(),
                    "Estado": status
                })
            
            df_table = pd.DataFrame(table_data)
            st.dataframe(df_table, use_container_width=True, hide_index=True)

    else:
        st.info("No hay tareas válidas para mostrar en el gráfico. ¡Agrega algunas en la tabla de arriba!")

except KeyError as e:
    st.error(f"**Error de Dependencia:** La tarea de la que dependes no se calculó bien. Detalles: {e}")
except Exception as e:
    st.error(f"Hubo un problema procesando los datos. Detalles técnicos: {e}")
