import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os

# Set up the webpage layout
st.set_page_config(layout="wide")
st.title("Interactive Project Gantt Chart")

default_start = datetime(2026, 2, 19).date()
csv_filename = "project_tasks.csv"

# 1. Database Logic: Load from CSV if it exists, otherwise use default data
if 'tasks' not in st.session_state:
    if os.path.exists(csv_filename):
        # Load saved data
        df = pd.read_csv(csv_filename)
        # Convert the 'Start Date' text back into actual Date objects
        df["Start Date"] = pd.to_datetime(df["Start Date"]).dt.date
        st.session_state['tasks'] = df
    else:
        # First-time setup default data
        st.session_state['tasks'] = pd.DataFrame([
            {"Task ID": "T1", "Task Name": "Project Kickoff", "Duration (Days)": 2, "Depends On": None, "Start Date": default_start},
            {"Task ID": "T2", "Task Name": "Market Research", "Duration (Days)": 5, "Depends On": "T1", "Start Date": None},
        ])

st.write("### 1. Edit the Project Schedule")
st.info("💡 **How to use:** Edit the table below. When you are done, click the **Save Changes** button so others can see your updates!")

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

# 3. Add a Save Button to write changes to our CSV "Database"
if st.button("💾 Save Changes for Everyone"):
    edited_df.to_csv(csv_filename, index=False)
    st.success("Changes successfully saved to the database!")

st.write("### 2. Project Timeline")

calculated_data = {}

try:
    for index, row in edited_df.iterrows():
        t_id = str(row["Task ID"])
        t_pre = row["Depends On"]
        t_duration = int(row["Duration (Days)"])
        t_manual_start = row["Start Date"]
        
        if pd.isna(t_pre) or t_pre is None or str(t_pre).strip() == "":
            if pd.notna(t_manual_start):
                t_start = t_manual_start
            else:
                t_start = default_start
        else:
            t_start = calculated_data[str(t_pre)]["Finish"] + timedelta(days=1)
            
        t_end = t_start + timedelta(days=t_duration)
        
        calculated_data[t_id] = {
            "Task": row["Task Name"],
            "Start": t_start,
            "Finish": t_end
        }
        
    final_df = pd.DataFrame(list(calculated_data.values()))
    
    fig = px.timeline(final_df, x_start="Start", x_end="Finish", y="Task", color="Task")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, width="stretch")

except KeyError as e:
    st.error(f"**Dependency Error:** Check your 'Depends On' column. Ensure task {e} exists.")
except Exception as e:
    st.error("Please ensure all fields are filled out correctly.")
  import subprocess
from google.colab import output
import time

# 1. Force-quit any old, stuck Streamlit servers
!pkill -f streamlit

# 2. Start the Streamlit app in the background with special proxy settings
print("Starting the Streamlit server...")
process = subprocess.Popen([
    "streamlit", "run", "app.py", 
    "--server.port", "8501", 
    "--server.enableCORS", "false", 
    "--server.enableXsrfProtection", "false"
])

# Give the server a couple of seconds to boot up completely
time.sleep(3)

# 3. Use Google Colab's built-in proxy to generate a secure, clickable link
print("Server is ready! Click the link below to open your app:")
output.serve_kernel_port_as_window(8501)
