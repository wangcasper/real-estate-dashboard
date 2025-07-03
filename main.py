import streamlit as st
import pandas as pd
from data_utils import (
    load_and_clean_multiple, add_months_since_ed, calc_monthly_summary
)
from plot_utils import plot_chart, plot_summary_table


st.set_page_config(page_title="Trautman Appraisal Dashboard", layout="wide")


if 'df_clsd' not in st.session_state or 'active_page' not in st.session_state:
    st.session_state.active_page = 'Home'


with st.sidebar:
    if 'df_clsd' in st.session_state:
        st.markdown("## Navigation")
        menu = st.radio("", ["Statistics", "Yearly Analysis", "Quarterly Analysis", "Monthly Analysis"])
        st.session_state.active_page = menu

        st.markdown("## Effective Date Range")
        col1, col2 = st.columns(2)

        start_ed = col1.date_input(
            "Start ED", pd.to_datetime(st.session_state.get('start_ed', "2020-01-01"))
        )
        end_ed = col2.date_input(
            "End ED", pd.to_datetime(st.session_state.get('end_ed', "2025-12-31"))
        )

        st.session_state.start_ed = start_ed
        st.session_state.end_ed = end_ed

        st.markdown("---")
        if st.button("🔄 Reload Data"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    else:
        st.markdown("🚀 Please upload data first.")


if st.session_state.active_page == 'Home':
    st.title("🏡 Trautman Appraisal Dashboard - Upload Data")
    uploaded_files = st.file_uploader(
        "Upload Appraisal Data (.xls or .xlsx)", type=['xlsx', 'xls'], accept_multiple_files=True
    )

    if uploaded_files:
        df = load_and_clean_multiple(uploaded_files)

        st.write(f"Loaded **{df.shape[0]}** closed records after removing duplicates.")
        st.write("Status count:")
        st.write(df['Status'].value_counts())

        st.session_state.df_clsd = df
        if 'start_ed' not in st.session_state:
            st.session_state.start_ed = pd.to_datetime("2020-01-01")
        if 'end_ed' not in st.session_state:
            st.session_state.end_ed = pd.to_datetime("2025-12-31")

        st.success("✅ Data loaded! Switching to **Statistics** tab...")
        st.session_state.active_page = 'Statistics'
        st.rerun()


if st.session_state.active_page == "Statistics":
    st.header("📈 Data Summary - Trautman Appraisal")

    if 'df_clsd' in st.session_state:
        df = st.session_state.df_clsd.copy()

        df = df[(df['Closed_Date'] >= pd.to_datetime(st.session_state.start_ed)) &
                (df['Closed_Date'] <= pd.to_datetime(st.session_state.end_ed))]

        df = add_months_since_ed(df, st.session_state.end_ed)

        st.subheader("📊 Property Status Summary")
        status_counts = df['Mapped_Status'].value_counts().to_dict()
        status_labels = ["Active", "Contingent", "Pending", "Sold"]

        st.write(f"Effective Date Range: **{st.session_state.start_ed.strftime('%Y-%m-%d')}** ➝ **{st.session_state.end_ed.strftime('%Y-%m-%d')}**")
        st.write(f"Number of records: **{df.shape[0]}**")

        st.subheader("✅ Filter by Status")
        selected_statuses = st.multiselect(
            "Select status:", options=status_labels, default=status_labels
        )
        df_filtered = df[df['Mapped_Status'].isin(selected_statuses)]
        st.session_state.df_filtered = df_filtered

        st.dataframe(df_filtered.head(5))

        st.markdown("---")
        st.subheader("📌 Key Summary Metrics")
        overall_median_price = df_filtered['Sold_Price'].median()
        overall_median_days = df_filtered['Market_Time'].median()
        total_properties = len(df_filtered)

        col1, col2, col3 = st.columns(3)
        col1.metric("Current Median Price", f"${int(overall_median_price):,}" if pd.notnull(overall_median_price) else "N/A")
        col2.metric("Current Median Days on Market", f"{int(overall_median_days)} days" if pd.notnull(overall_median_days) else "N/A")
        col3.metric("Total Properties", total_properties)

    else:
        st.warning("⚠️ Please upload data first on Home page!")


elif st.session_state.active_page == "Yearly Analysis":
    st.header("📊 Yearly Analysis")
    if 'df_filtered' in st.session_state:
        df = st.session_state.df_filtered.copy()

        df = df[(df['Closed_Date'] >= pd.to_datetime(st.session_state.start_ed)) &
                (df['Closed_Date'] <= pd.to_datetime(st.session_state.end_ed))]

        df['Year'] = df['Closed_Date'].dt.year.astype(str)

        summary = df.groupby('Year').agg(
            Median_Price=('Sold_Price', 'median'),
            Median_Days=('Market_Time', 'median'),
            Count=('Sold_Price', 'count')
        ).reset_index()

        year_list = pd.date_range(
            start=st.session_state.start_ed,
            end=st.session_state.end_ed,
            freq='YS'
        ).year.astype(str).tolist()

        chart_type = st.selectbox("Select Chart Type", ["line", "scatter", "histogram"])
        plot_chart(summary, "Year", chart_type, x_order=year_list)
        plot_summary_table(summary, "Year")
    else:
        st.warning("⚠️ Please upload data first on Home page!")


elif st.session_state.active_page == "Quarterly Analysis":
    st.header("📊 Quarterly Analysis")
    if 'df_filtered' in st.session_state:
        df = st.session_state.df_filtered.copy()

        df = df[(df['Closed_Date'] >= pd.to_datetime(st.session_state.start_ed)) &
                (df['Closed_Date'] <= pd.to_datetime(st.session_state.end_ed))]

        df['Year_Quarter'] = pd.PeriodIndex(df['Closed_Date'], freq='Q').astype(str)

        summary = df.groupby('Year_Quarter').agg(
            Median_Price=('Sold_Price', 'median'),
            Median_Days=('Market_Time', 'median'),
            Count=('Sold_Price', 'count')
        ).reset_index()

        quarter_list = pd.period_range(
            start=pd.to_datetime(st.session_state.start_ed),
            end=pd.to_datetime(st.session_state.end_ed),
            freq='Q'
        ).astype(str).tolist()

        chart_type = st.selectbox("Select Chart Type", ["line", "scatter", "histogram"])
        plot_chart(summary, "Year_Quarter", chart_type, x_order=quarter_list)
        plot_summary_table(summary, "Year_Quarter")
    else:
        st.warning("⚠️ Please upload data first on Home page!")


elif st.session_state.active_page == "Monthly Analysis":
    st.header("📊 Monthly Analysis")
    if 'df_filtered' in st.session_state:
        df = st.session_state.df_filtered.copy()

        df = df[(df['Closed_Date'] >= pd.to_datetime(st.session_state.start_ed)) &
                (df['Closed_Date'] <= pd.to_datetime(st.session_state.end_ed))]

        df['Closed_Month'] = df['Closed_Date'].dt.to_period('M').astype(str)

        summary = df.groupby('Closed_Month').agg(
            Median_Price=('Sold_Price', 'median'),
            Median_Days=('Market_Time', 'median'),
            Count=('Sold_Price', 'count')
        ).reset_index()

        month_list = pd.period_range(
            start=pd.to_datetime(st.session_state.start_ed),
            end=pd.to_datetime(st.session_state.end_ed),
            freq='M'
        ).astype(str).tolist()

        chart_type = st.selectbox("Select Chart Type", ["line", "scatter", "histogram"])
        plot_chart(summary, "Closed_Month", chart_type, x_order=month_list)
        plot_summary_table(summary, "Closed_Month")
    else:
        st.warning("⚠️ Please upload data first on Home page!")


st.markdown("---")
st.markdown("© 2025 Trautman Analytics - Appraisal Dashboard")
