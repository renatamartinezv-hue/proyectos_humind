import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# Set up the webpage layout
st.set_page_config(layout="wide")
st.title("Interactive Project Gantt Chart")

# Paste your ENTIRE Google Sheets URL here
SHEET_URL = "https://docs.google.com/spreadsheets/d/1O8aZdaPzIiYDreFA_9yRdfjOd9oMRy2TpAnl3mDwTBY/edit?gid=0#gid=0" 

# Establish a connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

default_start = datetime(2026, 2, 19).date()

# 1. Database Logic: Load from Google Sheets
try:
    # Read the data. ttl=0 ensures we bypass the cache and always get the live data
    df = conn.read(spreadsheet=SHEET_URL, worksheet=TAB_NAME, ttl=0)
    
    # Google Sheets might return empty rows; drop them to keep things clean
    df = df.dropna(how="all") 
    
    # If the sheet is completely empty, load our default starter data
    if df.empty:
        st.session_state['tasks'] = pd.DataFrame([
            {"Task ID": "T1", "Task Name": "Project Kickoff", "Duration (Days)": 2, "Depends On": None, "Start Date": default_start},
            {"Task ID": "T2", "Task Name": "Market Research", "Duration (Days)": 5, "Depends On": "T1", "Start Date": None},
        ])
    else:
        # Convert the text dates from Google back into actual Python Date objects
        df["Start Date"] = pd.to_datetime(df["Start Date"], errors='coerce').dt.date
        st.session_state['tasks'] = df

except Exception as e:
    st.error(f"Could not connect to Google Sheets. Check your Secrets and Sheet ID! Error: {e}")
    st.stop()

st.write("### 1. Edit the Project Schedule")
st.info("💡 **How to use:** Edit the table below. When you are done, click the **Save Changes** button to update the live Google Sheet!")

# 2. Create the Data Editor
edited_df = st.data_editor(
    st.session_state['tasks'], 
    num_rows="dynamic", 
    width="stretch",
    column_config={
        "Task ID": st.column_config.TextColumn("Task ID", required=True),
        "Task Name": st.column_config.TextColumn("Task Name", required=True),
        "Duration (Days)": st.column_config.NumberColumn("Duration (Days)", min_value=1, step=1, required=True),
        "Depends On": st.column_config.TextColumn("Depends On (Task ID)"),
        "Start Date": st.column_config.DateColumn("Start Date (If Independent)", format="YYYY-MM-DD"),
    }
)

# 3. Add a Save Button to write changes to Google Sheets
if st.button("💾 Save Changes to Google Sheets"):
    try:
        conn.update(spreadsheet=SHEET_URL, worksheet=TAB_NAME, data=edited_df)
        st.success("Changes successfully saved to the live database!")
        st.cache_data.clear() # Clear memory so the next load is fresh
    except Exception as e:
        st.error(f"Failed to save: {e}")

st.write("### 2. Project Timeline")

calculated_data = {}

try:
    for index, row in edited_df.iterrows():
        t_id = str(row["Task ID"])
        t_pre = row["Depends On"]
        t_duration = int(row["Duration (Days)"])
        t_manual_start = row["Start Date"]
        
        # Scenario B: Independent Task
        if pd.isna(t_pre) or t_pre is None or str(t_pre).strip() == "":
            if pd.notna(t_manual_start):
                t_start = t_manual_start
            else:
                t_start = default_start
        # Scenario A: Dependent Task
        else:
            t_start = calculated_data[str(t_pre)]["Finish"] + timedelta(days=1)
            
        t_end = t_start + timedelta(days=t_duration)
        
        calculated_data[t_id] = {
            "Task": row["Task Name"],
            "Start": t_start,
            "Finish": t_end
        }
        
    final_df = pd.DataFrame(list(calculated_data.values()))
    
    # Plot the Gantt Chart
    fig = px.timeline(final_df, x_start="Start", x_end="Finish", y="Task", color="Task")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, width="stretch")

except KeyError as e:
    st.error(f"**Dependency Error:** Check your 'Depends On' column. Ensure task {e} exists.")
except Exception as e:
    st.error("Please ensure all fields are filled out correctly.")
