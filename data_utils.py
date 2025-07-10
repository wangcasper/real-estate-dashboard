# data_utils.py
import pandas as pd
import streamlit as st

def get_file_summary(df, file_name):
    row_count = len(df)
    stat_counts = df['Stat'].value_counts().to_dict() if 'Stat' in df.columns else {}
    return {
        'file_name': file_name,
        'row_count': row_count,
        'stat_counts': stat_counts
    }

def load_and_clean_data(df):
    # Convert date columns
    df['Closed_Date'] = pd.to_datetime(df['Closed_Date'])
    df['Contract_Date'] = pd.to_datetime(df['Contract_Date'])

    # Remove full-row duplicates
    before_dedup = len(df)
    df = df.drop_duplicates()
    after_dedup = len(df)
    removed_count = before_dedup - after_dedup

    # Show deduplication result
    if removed_count > 0:
        st.info(f"🧹 Removed {removed_count} duplicate rows during cleaning.")
    else:
        st.success("✅ No duplicate rows found.")

    # Map status values
    df['Mapped_Status'] = df['Status'].apply(map_status)

    return df


def map_status(status):
    status = str(status).strip().upper()

    active_status = [
        'ACTV', 'BOMK', 'NEW', 'RACT', 'PCHG', 'TEMP', 'AUCT',
        'PRIV-ACTV', 'A', 'PR', 'BOM', 'LCS', 'ACTIVE', 'ACT'
    ]

    contingent_status = [
        'A/I', 'CTGA', 'CTGO', 'HC24', 'HC48', 'HC72',
        'HS24', 'HS48', 'HS72', 'HS', 'SS', 'PRIV-CTG',
        'COBU', 'CO3PA', 'COSD', 'COFR', 'COO', 'PRE-MARKET', 'AUC',
        'FIN'
    ]

    pending_status = [
        'PEND', 'PRIV-PEND', 'P', 'PENDING', 'PND'
    ]

    sold_status = [
        'CLSD', 'S', 'SC', 'SOLD','CLOSED'
    ]

    if status in active_status:
        return "Active"
    elif status in contingent_status:
        return "Contingent"
    elif status in pending_status:
        return "Pending"
    elif status in sold_status:
        return "Closed"
    else:
        raise ValueError(f"❌ Unrecognized status: '{status}'. Please check your data.")

def add_months_since_ed(df, ed_date):
    df['Months_Since_ED'] = (pd.to_datetime(ed_date).to_period('M') - df['Closed_Date'].dt.to_period('M')).apply(lambda x: x.n if pd.notnull(x) else None)
    return df


def get_date_range_input():
    if 'start_ed' not in st.session_state:
        st.session_state.start_ed = st.session_state.ed_date - pd.DateOffset(years=5)
    if 'end_ed' not in st.session_state:
        st.session_state.end_ed = st.session_state.ed_date

    start_ed = st.date_input("Select Start Date", value=st.session_state.start_ed)
    end_ed = st.date_input("Select End Date", value=st.session_state.end_ed)

    if start_ed > end_ed:
        st.warning("⚠️ Start date must be before or equal to end date.")
        st.stop()

    st.session_state.start_ed = start_ed
    st.session_state.end_ed = end_ed

    return start_ed, end_ed

def get_month_range_input():
    month_range = pd.period_range(
        start=st.session_state.ed_date - pd.DateOffset(years=5),
        end=st.session_state.ed_date,
        freq='M'
    ).to_timestamp()

    month_options = month_range.strftime("%Y-%m").tolist()
    total_months = len(month_options)

    # Default range: last 12 months
    if total_months >= 13:
        default_start_index = total_months - 13
    else:
        default_start_index = 0

    start_month = st.selectbox("Select Start Month", options=month_options, index=default_start_index)
    end_month = st.selectbox("Select End Month", options=month_options, index=total_months - 1)

    start_ed = pd.to_datetime(start_month)
    end_ed = pd.to_datetime(end_month) + pd.offsets.MonthEnd(0)

    if start_ed > end_ed:
        st.warning("⚠️ Start month must be before or equal to end month.")
        st.stop()

    return start_ed, end_ed


def get_year_range_input():
    current_year = st.session_state.ed_date.year
    year_range = list(range(current_year - 5, current_year + 1))

    start_year = st.selectbox("Select Start Year", options=year_range, index=0)
    end_year = st.selectbox("Select End Year", options=year_range, index=len(year_range) - 1)

    if start_year > end_year:
        st.warning("⚠️ Start year must be before or equal to end year.")
        st.stop()

    start_ed = pd.to_datetime(f"{start_year}-01-01")
    end_ed = pd.to_datetime(f"{end_year}-12-31")

    return start_ed, end_ed

def generate_12_month_summary(df):
    closed_sales = df[df['Mapped_Status'] == 'Closed']
    median_time = int(closed_sales['Market_Time'].median()) if not closed_sales.empty else 0
    median_price = int(closed_sales['Sold_Price'].median()) if not closed_sales.empty else 0
    closed_count = closed_sales.shape[0]

    summary = (
        f"<span style='color:red; font-weight:bold'>{closed_count}</span> closed sales with a median market time of "
        f"<span style='color:red; font-weight:bold'>{median_time}</span> days and median sales price of "
        f"<span style='color:red; font-weight:bold'>${median_price:,.0f}</span>."
    )
    return summary


def generate_listing_summary(df_all, ed_date):
    one_year_ago = pd.Timestamp(ed_date) - pd.DateOffset(months=12)

    # Count all active listings (no date filtering)
    active_count = df_all[df_all['Mapped_Status'] == 'Active'].shape[0]

    recent_df = df_all[df_all['Contract_Date'] >= one_year_ago]
    cont_pend_count = recent_df[recent_df['Mapped_Status'].isin(['Contingent', 'Pending'])].shape[0]

    listing_summary = (
        f"There are currently <span style='color:red; font-weight:bold'>{active_count}</span> active listings and "
        f"<span style='color:red; font-weight:bold'>{cont_pend_count}</span> contingent/pending listings in the search parameter defined above."
    )
    return listing_summary






