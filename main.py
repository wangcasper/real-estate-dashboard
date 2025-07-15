# main.py
import streamlit as st
import pandas as pd
from datetime import timedelta
import altair as alt
from data_utils import get_file_summary, load_and_clean_data, add_months_since_ed, get_month_range_input, get_year_range_input, get_date_range_input, generate_12_month_summary, generate_listing_summary
from plot_utils import plot_chart, plot_summary_table, plot_individual_scatter, plot_combo_chart_with_table

# Streamlit config
st.set_page_config(page_title="Trautman Appraisal Dashboard", layout="wide")

DEFAULT_ED_DATE = "2025-07-07"
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
        ed_date = st.date_input("Select ED", pd.to_datetime(st.session_state.get('ed_date', DEFAULT_ED_DATE)))
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
                    st.session_state.ed_date = pd.to_datetime(DEFAULT_ED_DATE)

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

        # ---- 📌 Extended Summary Metrics by 12-Month Periods ----
        st.markdown("---")
        st.subheader("📌 Summary Metrics by 12-Month Periods")
        period_end = pd.Timestamp(st.session_state.ed_date)

        for i in range(5):
            if i == 0:
                period_start = period_end - pd.DateOffset(years=1)
            else:
                period_end = period_start - timedelta(days=1)
                period_start = period_end - pd.DateOffset(years=1) + timedelta(days=1)

            period_label = f"{i*12}–{(i+1)*12} Month Summary"
            st.markdown(f"**📆 {period_label}**  \nDate Range: **{period_end.date()}** to **{period_start.date()}**")
            df_period = df_filtered[
                (df_filtered['Closed_Date'] <= period_end) &
                (df_filtered['Closed_Date'] >= period_start)
            ]

            if not df_period.empty:
                median_price = df_period['Sold_Price'].median()
                median_days = df_period['Market_Time'].median()
                total_properties = len(df_period)

                col1, col2, col3 = st.columns(3)
                col1.metric("Median Price", f"${int(median_price):,}" if pd.notna(median_price) else "N/A")
                col2.metric("Median Days", f"{int(median_days)} days" if pd.notna(median_days) else "N/A")
                col3.metric("Total Properties", total_properties)

                summary_text = generate_12_month_summary(df_period)
                if i == 0:
                    listing_text = generate_listing_summary(df_filtered, st.session_state.ed_date)
                    st.markdown(summary_text, unsafe_allow_html=True)
                    st.markdown(listing_text, unsafe_allow_html=True)
                else:
                    st.markdown(summary_text, unsafe_allow_html=True)
            else:
                st.info("ℹ️ No data available in this period.")
            st.markdown("---")


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
        df = df[df['Mapped_Status'] == 'Closed']

        ed_date = pd.Timestamp(st.session_state.ed_date)

        summary_data = []
        for i in range(5):
            if i == 0:
                period_end = ed_date
                period_start = period_end - pd.DateOffset(years=1)
            else:
                period_end = period_start - timedelta(days=1)
                period_start = period_end - pd.DateOffset(years=1) + timedelta(days=1)

            df_period = df[(df['Closed_Date'] >= period_start) & (df['Closed_Date'] <= period_end)]
            if df_period.empty:
                continue

            summary_data.append({
                "Period": f"{i*12}–{(i+1)*12} Month",
                "Date_Range": f"{period_start.date()} to {period_end.date()}",
                "Median_Price": df_period['Sold_Price'].median(),
                "Median_Days": df_period['Market_Time'].median(),
                "Count": df_period.shape[0],
                "Sort_Key": i
            })

        summary = pd.DataFrame(summary_data)
        summary = summary.sort_values(by="Sort_Key", ascending=False).reset_index(drop=True)
        summary.drop(columns="Sort_Key", inplace=True)

        if summary.empty:
            st.warning("⚠️ No data available in the 5-year period.")
        else:
            st.subheader("📊 12-Month Rolling Summary (Based on Effective Date)")

            # ✅ Add slider to select range
            available_periods = summary["Period"].tolist()
            start_label, end_label = st.select_slider(
                "Select Period Range to Display",
                options=available_periods,
                value=(available_periods[0], available_periods[-1])
            )

            start_index = available_periods.index(start_label)
            end_index = available_periods.index(end_label)
            selected_periods = available_periods[start_index:end_index + 1]

            summary_selected = summary[summary["Period"].isin(selected_periods)]
            x_order = summary_selected["Period"].tolist()

            # 🔹 Chart + Table
            plot_combo_chart_with_table(summary_selected, x_col="Period", x_order=x_order)

            st.markdown("---")
            chart_type = st.selectbox("Select Chart Type", ["line", "scatter", "histogram"])
            plot_chart(summary_selected, x_col="Period", chart_type=chart_type, x_order=x_order)
            plot_summary_table(summary_selected, x_col="Period")

    else:
        st.warning("⚠️ Please upload data first on Home page!")



# Quarterly Analysis
elif st.session_state.active_page == "Quarterly Analysis":
    st.header("📊 Quarterly Analysis")

    if 'df_filtered' in st.session_state:
        df = st.session_state.df_filtered.copy()
        ed = st.session_state.ed_date

        # Create rolling 3-month custom quarters: Q1 (most recent) to Q20 (oldest)
        quarter_ranges = []
        for i in range(20):
            end_date = ed - pd.DateOffset(months=3 * i)
            start_date = end_date - pd.DateOffset(months=3)
            if i > 0:
                end_date = ed - pd.DateOffset(months=3 * i) - pd.Timedelta(days=1)
                start_date = end_date - pd.DateOffset(months=3) + pd.Timedelta(days=1)
            quarter_ranges.append({
                "Quarter": f"Q{i+1}",
                "Start_Date": start_date,
                "End_Date": end_date
            })

        quarter_ranges = quarter_ranges[::-1]
        quarter_labels = [q["Quarter"] for q in quarter_ranges]

        # 🎯 Set default range: Q1 to Q8 (most recent 8 quarters)
        q_start, q_end = st.select_slider(
            'Select Quarter Range to Display',
            options=quarter_labels,
            value=(quarter_labels[-1], quarter_labels[-8])  # Q1 ~ Q8
        )

        start_index = quarter_labels.index(q_start)
        end_index = quarter_labels.index(q_end)
        selected_quarters = quarter_labels[start_index:end_index + 1]

        # ℹ️ Show quarter definitions
        with st.expander("ℹ️ Quarter Definitions (from Effective Date)"):
            for qr in quarter_ranges:
                st.markdown(f"- **{qr['Quarter']}** = {qr['Start_Date'].date()} to {qr['End_Date'].date()}")

        # 📊 Filter & summarize data
        summary_data = []
        for q in quarter_ranges:
            if q["Quarter"] not in selected_quarters:
                continue

            start_q, end_q = q["Start_Date"], q["End_Date"]
            df_q = df[(df['Closed_Date'] >= start_q) & (df['Closed_Date'] <= end_q)]
            if df_q.empty:
                continue

            summary_data.append({
                "Quarter": q["Quarter"],
                "Median_Price": df_q['Sold_Price'].median(),
                "Median_Days": df_q['Market_Time'].median(),
                "Count": df_q.shape[0],
                "Date_Range": f"{start_q.date()} to {end_q.date()}"
            })

        # 📈 Create summary DataFrame in selected order
        summary = pd.DataFrame(summary_data)
        summary = summary.set_index("Quarter").reindex(selected_quarters).dropna().reset_index()

        if summary.empty:
            st.warning("⚠️ No data available for selected quarters.")
        else:
            start_label = summary["Quarter"].iloc[0]
            end_label = summary["Quarter"].iloc[-1]
            st.subheader(f"📊 Quarterly Summary ({start_label} to {end_label})")

            x_order = summary["Quarter"].tolist()

            plot_combo_chart_with_table(summary, x_col="Quarter", x_order=x_order)

            st.markdown("---")
            chart_type = st.selectbox("Select Chart Type", ["line", "scatter", "histogram"])
            plot_chart(summary, "Quarter", chart_type=chart_type, x_order=x_order)
            plot_summary_table(summary, "Quarter")

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

        start_label = month_list[0]
        end_label = month_list[-1]
        st.subheader(f"📊 Monthly Summary ({start_label} to {end_label})")

        plot_combo_chart_with_table(summary, x_col="Closed_Month", x_order=month_list)

        st.markdown("---")
        chart_type = st.selectbox("Select Chart Type", ["line", "scatter", "histogram"])
        plot_chart(summary, "Closed_Month", chart_type, x_order=month_list)
        plot_summary_table(summary, "Closed_Month")

    else:
        st.warning("⚠️ Please upload data first on Home page!")

# Individual Analysis
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
