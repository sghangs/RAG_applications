import streamlit as st
import pandas as pd
import os
import json

# --- Load All Runs ---
result_dir = "data/evaluation_results"
runs = sorted(os.listdir(result_dir), reverse=True)

st.set_page_config(page_title="RAG Evaluation Dashboard", layout="wide")
st.title("📊 RAG Evaluation Dashboard")

# --- Sidebar to Select a Run ---
selected_run = st.sidebar.selectbox("📁 Select Evaluation Run", runs)

# --- Load Results ---
csv_path = os.path.join(result_dir, selected_run, "results.csv")
json_path = os.path.join(result_dir, selected_run, "results.json")

if not os.path.exists(csv_path):
    st.error("Results not found in selected folder.")
    st.stop()

df = pd.read_csv(csv_path)
with open(json_path) as f:
    raw_data = json.load(f)

# --- Summary Stats ---
st.markdown(f"**Run Time:** `{selected_run}`")
col1, col2, col3 = st.columns(3)
col1.metric("🧪 Total Cases", len(df))
col2.metric("✅ Passed", df['Success'].sum())
col3.metric("📈 Avg Score", round(df['Score'].mean(), 3))

# --- Filters ---
show_failures = st.checkbox("Show only failed cases", value=False)
filtered_df = df[~df['Success']] if show_failures else df

# --- Table View ---
st.dataframe(filtered_df[["Input", "Score", "Success", "Reason"]], use_container_width=True)

# --- Detailed Viewer ---
st.subheader("🔍 Inspect a Test Case")
case_idx = st.number_input("Choose test case number", min_value=1, max_value=len(raw_data), step=1)
case = raw_data[case_idx - 1]

st.markdown("**Input:**")
st.code(case["Input"])
st.markdown("**Expected Output:**")
st.code(case["Expected Output"])
st.markdown("**Actual Output:**")
st.code(case["Actual Output"])
st.markdown(f"**Score:** {case['Score']} | **Passed:** {case['Success']}")
st.markdown(f"**Reason:** {case['Reason']}")