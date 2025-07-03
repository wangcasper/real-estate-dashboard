import streamlit as st
import altair as alt
import pandas as pd


def convert_x_to_numeric(df, x_col):
    if x_col == "Year":
        return df[x_col].astype(int)
    elif x_col == "Year_Quarter":
        return df[x_col].apply(lambda x: convert_quarter_to_number(x))
    elif x_col == "Closed_Month":
        return df[x_col].apply(lambda x: pd.Period(x, freq='M').to_timestamp().timestamp() / 1e10)
    else:
        return pd.Series(range(len(df)))


def convert_quarter_to_number(quarter_str):
    year, q = quarter_str.split('Q')
    return int(year) + (int(q) - 1) * 0.25


def plot_chart(df, x_col, chart_type="line", y_col="Median_Price", x_order=None):
    st.subheader("📈 Custom Chart")

    df = df.copy()
    df['X_Num'] = convert_x_to_numeric(df, x_col)

    # 主圖（分類軸，顯示正常 Label）
    base = None
    encodings = {
        'x': alt.X(f'{x_col}:N', title='Period', sort=x_order),
        'y': alt.Y(f'{y_col}:Q', title=y_col.replace("_", " ")),
        'tooltip': [x_col, y_col, 'Count']
    }

    if chart_type == "line":
        base = alt.Chart(df).mark_line(point=True).encode(**encodings)
    elif chart_type == "scatter":
        base = alt.Chart(df).mark_circle(size=60).encode(**encodings)
    elif chart_type == "histogram":
        base = alt.Chart(df).mark_bar().encode(**encodings)
    else:
        st.error("❌ Unsupported chart type")
        return

    # 趨勢線（用數值 X 軸來跑 regression）
    trend = alt.Chart(df).transform_regression(
        'X_Num', y_col
    ).mark_line(color='red')

    trend = trend.encode(
        x=alt.X('X_Num:Q', title='Period'),
        y=alt.Y(f'{y_col}:Q'),
    )

    final_chart = (base + trend).properties(
        width=800,
        height=400
    )

    st.altair_chart(final_chart, use_container_width=True)


def plot_summary_table(df, x_col):
    st.subheader("📌 Summary Table")
    summary_df = df.rename(columns={
        x_col: 'Period',
        'Median_Price': 'Median Price',
        'Median_Days': 'Median Days on Market',
        'Count': 'Number of Properties'
    })
    st.dataframe(summary_df)



