import pandas as pd


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
        'CLSD', 'S', 'SC', 'SOLD'
    ]

    if status in active_status:
        return "Active"
    elif status in contingent_status:
        return "Contingent"
    elif status in pending_status:
        return "Pending"
    elif status in sold_status:
        return "Sold"
    else:
        raise ValueError(f"❌ Unrecognized status: '{status}'. Please check your data.")


def load_and_clean_data(uploaded_file):
    df = pd.read_excel(uploaded_file, engine='openpyxl')

    # 標準化欄位名稱
    df.columns = [c.strip().replace('MLS #', 'MLS_Number')
                          .replace('Contract Date', 'Contract_Date')
                          .replace('Closed Date', 'Closed_Date')
                          .replace('Sold Pr', 'Sold_Price')
                          .replace('MT', 'Market_Time')
                          .replace('Stat', 'Status')
                          for c in df.columns]

    df['Closed_Date'] = pd.to_datetime(df['Closed_Date'], errors='coerce')
    df['Contract_Date'] = pd.to_datetime(df['Contract_Date'], errors='coerce')

    df['Mapped_Status'] = df['Status'].apply(map_status)

    return df


def load_and_clean_multiple(files):
    combined_df = pd.DataFrame()

    for file in files:
        df = load_and_clean_data(file)
        combined_df = pd.concat([combined_df, df], ignore_index=True)

    combined_df = combined_df.drop_duplicates(subset=['MLS_Number', 'Closed_Date'])
    return combined_df


def add_months_since_ed(df, ed_date):
    df['Months_Since_ED'] = (
        pd.to_datetime(ed_date).to_period('M') - df['Closed_Date'].dt.to_period('M')
    ).apply(lambda x: x.n if pd.notnull(x) else None)
    return df


def calc_monthly_summary(df):
    df['Closed_Month'] = df['Closed_Date'].dt.to_period('M').astype(str)
    summary = df.groupby('Closed_Month').agg(
        Median_Price=('Sold_Price', 'median'),
        Median_Days=('Market_Time', 'median'),
        Count=('Sold_Price', 'count')
    ).reset_index().dropna()

    return summary
