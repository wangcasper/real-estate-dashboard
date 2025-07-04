# main.py
import streamlit as st
import pandas as pd
import altair as alt
from data_utils import get_file_summary, load_and_clean_data, add_months_since_ed, get_month_range_input, get_year_range_input, get_date_range_input, generate_12_month_summary
from plot_utils import plot_chart, plot_summary_table, plot_individual_scatter

# Streamlit config
st.set_page_config(page_title="Trautman Appraisal Dashboard", layout="wide")

# Init state
if 'df_clsd' not in st.session_state or 'active_page' not in st.session_state:
    st.session_state.active_page = 'Home'

# Sidebar
with st.sidebar:
    if 'df_clsd' in st.session_state:
        st.markdown("## Navigation")
        menu = st.radio("", ["Statistics", "Yearly Analysis", "Quarterly Analysis", "Monthly Analysis", "Individual Analysis"])
        st.session_state.active_page = menu

        st.markdown("## Effective Date (ED)")
        ed_date = st.date_input("Select ED", pd.to_datetime(st.session_state.get('ed_date', "2025-06-17")))
        st.session_state.ed_date = ed_date

        st.markdown("---")
        if st.button("🔄 Reload Data"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    else:
        st.markdown("🚀 Please upload data first.")
# Home Upload Page
if st.session_state.active_page == 'Home':
    st.title("🏡 Trautman Appraisal Dashboard - Upload Data")
    uploaded_files = st.file_uploader("Upload one or more Excel files (.xlsx)", type=['xlsx'], accept_multiple_files=True)

    if uploaded_files:
        # Reset confirmation state if the uploaded files changed
        uploaded_names = [f.name for f in uploaded_files]
        if st.session_state.get('last_uploaded_files') != uploaded_names:
            st.session_state.file_summaries = []
            st.session_state.ready_to_analyze = False
            st.session_state.last_uploaded_files = uploaded_names

        expected_columns = ['MLS #', 'Contract Date', 'Closed Date', 'Sold Pr', 'MT', 'Stat']
        all_valid = True
        dataframes = []

        for file in uploaded_files:
            if not file.name.endswith('.xlsx'):
                st.error(f"❌ `{file.name}` is not an Excel file.")
                all_valid = False
                break

            try:
                df_raw = pd.read_excel(file)
            except Exception as e:
                st.error(f"❌ Failed to read `{file.name}`. Error: {e}")
                all_valid = False
                break

            if list(df_raw.columns[:6]) != expected_columns:
                st.error(f"""❌ Column mismatch in `{file.name}`.
The first six columns must exactly match (in order):
1. MLS #
2. Contract Date
3. Closed Date
4. Sold Pr
5. MT
6. Stat""")
                all_valid = False
                break

            dataframes.append((file.name, df_raw))

        # Show Confirm Files button only if all are valid
        if all_valid:
            st.success(f"✅ {len(uploaded_files)} file(s) passed format check.")
            if st.button("📋 Confirm Files"):
                st.session_state.file_summaries = []
                for name, df in dataframes:
                    summary = get_file_summary(df, name)
                    st.session_state.file_summaries.append(summary)
                st.session_state.ready_to_analyze = True

        # Show summary info after confirmation
        if st.session_state.get('ready_to_analyze', False):
            st.subheader("📄 Uploaded File Summary")
            for summary in st.session_state.file_summaries:
                st.markdown(f"**📁 {summary['file_name']}**")
                st.write(f"- Total Rows: {summary['row_count']}")
                st.write("- `Stat` Value Counts:")
                st.write(summary['stat_counts'])
            dfs = []
            for _, df in dataframes:
                df.columns = ['MLS_Number', 'Contract_Date', 'Closed_Date', 'Sold_Price', 'Market_Time', 'Status']
                dfs.append(df)

            df_all = pd.concat(dfs, ignore_index=True)
            df_cleaned = load_and_clean_data(df_all)

            if st.button("🔍 Start Analysis"):
                st.session_state.df_clsd = df_cleaned
                st.session_state.ready_to_analyze = False
                if 'ed_date' not in st.session_state:
                    st.session_state.ed_date = pd.to_datetime("2025-06-17")

                st.success("✅ Data loaded! Switching to **Statistics** tab...")
                st.session_state.active_page = 'Statistics'
                st.rerun()


# --- Pages ---

# Statistics Page
if st.session_state.active_page == "Statistics":
    st.header("📈 Data Summary - Trautman Appraisal")

    if 'df_clsd' in st.session_state:
        df = add_months_since_ed(st.session_state.df_clsd.copy(), st.session_state.ed_date)

        st.write(f"Effective Date (ED): **{st.session_state.ed_date.strftime('%Y-%m-%d')}**")
        st.write(f"Number of records: **{df.shape[0]}**")

        # ---- Property Status Summary ----
        st.subheader("📊 Property Status Summary")
        status_counts = df['Mapped_Status'].value_counts().to_dict()
        status_labels = ["Active", "Contingent", "Pending", "Closed"]

        count_cols = st.columns(4)
        for i, status in enumerate(status_labels):
            count = status_counts.get(status, 0)
            count_cols[i].markdown(f"""
                <div style='padding:10px;border-radius:10px;border:2px solid #e0e0e0;text-align:center;'>
                    <span style='font-size:20px;font-weight:bold'>{status}: {count}</span>
                </div>
            """, unsafe_allow_html=True)

        # ---- Status Filter ----
        st.subheader("✅ Filter by Status")
        selected_statuses = st.multiselect("Select status:", options=status_labels, default=status_labels)

        df_filtered = df[df['Mapped_Status'].isin(selected_statuses)]
        st.write(f"**Showing {len(df_filtered)} of {len(df)} properties(Filter by Status)**")
        st.dataframe(df_filtered.head(5))
        st.session_state.df_filtered = df_filtered

        # ---- 📌 Key Metrics Summary ----
        st.markdown("---")
        st.subheader("📌 Key Summary Metrics")
        overall_median_price = df_filtered['Sold_Price'].median()
        overall_median_days = df_filtered['Market_Time'].median()
        total_properties = len(df_filtered)

        col1, col2, col3 = st.columns(3)
        col1.metric("Current Median Price", f"${int(overall_median_price):,}")
        col2.metric("Current Median Days on Market", f"{int(overall_median_days)} days")
        col3.metric("Total Properties", total_properties)

        # ---- 📅 0–12 Month Summary ----
        st.markdown("---")
        st.subheader("🕐 0–12 Month Summary")
        summary_text = generate_12_month_summary(df_filtered, st.session_state.ed_date)
        st.markdown(summary_text)

        # --- 📌 Missing Values ---
        st.markdown("---")
        st.subheader("📌 Missing Values Check")

        na_counts = df_filtered.isna().sum()
        na_counts = na_counts[na_counts > 0]
        df_missing = df_filtered[df_filtered.isna().any(axis=1)]

        if not na_counts.empty:
            st.write("⚠️ The following columns have missing values:")
            st.dataframe(na_counts.rename("Missing Count"))
            st.dataframe(df_missing)
        else:
            st.success("✅ No missing values detected in the current data.")



    else:
        st.warning("⚠️ Please upload data first on Home page!")

# Yearly Analysis
elif st.session_state.active_page == "Yearly Analysis":
    st.header("📊 Yearly Analysis")
    if 'df_filtered' in st.session_state:
        df = st.session_state.df_filtered.copy()

        start_ed, end_ed = get_year_range_input()
        df = df[(df['Closed_Date'] >= pd.to_datetime(start_ed)) &
                (df['Closed_Date'] <= pd.to_datetime(end_ed))]

        df['Year'] = df['Closed_Date'].dt.year.astype(str)

        # Build ordered list of all years in range
        year_list = pd.date_range(start=start_ed, end=end_ed, freq='YS').year.astype(str).tolist()

        # Group and reindex to preserve order
        summary = df.groupby('Year').agg(
            Median_Price=('Sold_Price', 'median'),
            Median_Days=('Market_Time', 'median'),
            Count=('Sold_Price', 'count')
        ).reindex(year_list).reset_index()
        summary = summary.rename(columns={"index": "Year"})

        chart_type = st.selectbox("Select Chart Type", ["line", "scatter", "histogram"])
        plot_chart(summary, "Year", chart_type, x_order=year_list)
        plot_summary_table(summary, "Year")
    else:
        st.warning("⚠️ Please upload data first on Home page!")


# Quarterly Analysis
elif st.session_state.active_page == "Quarterly Analysis":
    st.header("📊 Quarterly Analysis")
    if 'df_filtered' in st.session_state:
        df = st.session_state.df_filtered.copy()

        start_ed, end_ed = get_month_range_input()
        df = df[(df['Closed_Date'] >= pd.to_datetime(start_ed)) &
                (df['Closed_Date'] <= pd.to_datetime(end_ed))]

        df['Year_Quarter'] = pd.PeriodIndex(df['Closed_Date'], freq='Q').astype(str)

        quarter_list = pd.period_range(start=start_ed, end=end_ed, freq='Q').astype(str).tolist()

        summary = df.groupby('Year_Quarter').agg(
            Median_Price=('Sold_Price', 'median'),
            Median_Days=('Market_Time', 'median'),
            Count=('Sold_Price', 'count')
        ).reindex(quarter_list).reset_index()
        summary = summary.rename(columns={"index": "Year_Quarter"})

        # Optional: remove rows with no data
        summary = summary.dropna(subset=["Median_Price"])

        chart_type = st.selectbox("Select Chart Type", ["line", "scatter", "histogram"])
        plot_chart(summary, "Year_Quarter", chart_type, x_order=quarter_list)
        plot_summary_table(summary, "Year_Quarter")
    else:
        st.warning("⚠️ Please upload data first on Home page!")



# Monthly Analysis
elif st.session_state.active_page == "Monthly Analysis":
    st.header("📊 Monthly Analysis")
    if 'df_filtered' in st.session_state:
        df = st.session_state.df_filtered.copy()

        start_ed, end_ed = get_month_range_input()
        df = df[(df['Closed_Date'] >= pd.to_datetime(start_ed)) &
                (df['Closed_Date'] <= pd.to_datetime(end_ed))]

        df['Closed_Month'] = df['Closed_Date'].dt.to_period('M').astype(str)

        month_list = pd.period_range(start=start_ed, end=end_ed, freq='M').astype(str).tolist()

        summary = df.groupby('Closed_Month').agg(
            Median_Price=('Sold_Price', 'median'),
            Median_Days=('Market_Time', 'median'),
            Count=('Sold_Price', 'count')
        ).reindex(month_list).reset_index()
        summary = summary.rename(columns={"index": "Closed_Month"})

        # Optional: remove rows with no data
        summary = summary.dropna(subset=["Median_Price"])

        chart_type = st.selectbox("Select Chart Type", ["line", "scatter", "histogram"])
        plot_chart(summary, "Closed_Month", chart_type, x_order=month_list)
        plot_summary_table(summary, "Closed_Month")
    else:
        st.warning("⚠️ Please upload data first on Home page!")

elif st.session_state.active_page == "Individual Analysis":
    st.header("🔍 Individual Property Scatter Plot")
    if 'df_filtered' in st.session_state:
        df = st.session_state.df_filtered.copy()

        start_ed, end_ed = get_date_range_input()
        df = df[(df['Closed_Date'] >= pd.to_datetime(start_ed)) &
                (df['Closed_Date'] <= pd.to_datetime(end_ed))]

        st.write(f"Showing {len(df)} records")
        plot_individual_scatter(df)
    else:
        st.warning("⚠️ Please upload data first on Home page!")


# Footer
st.markdown("---")
st.markdown("© 2025 Trautman Analytics - Appraisal Dashboard")
