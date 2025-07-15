import streamlit as st
import altair as alt
import pandas as pd
import numpy as np

def convert_x_to_numeric(df, x_col):
    if x_col == "Year":
        return df[x_col].astype(int)
    elif x_col == "Year_Quarter":
        return df[x_col].apply(lambda x: convert_quarter_to_number(x))
    elif x_col == "Closed_Month":
        return df[x_col].apply(lambda x: pd.Period(x, freq='M').to_timestamp().timestamp() / 1e10)
    elif x_col == "Period" and df[x_col].str.contains('–').all():
        # Extract the first number (e.g., 48 from "48–60 Month")
        return df[x_col].str.extract(r'^(\d+)')[0].astype(float)
    else:
        return pd.Series(range(len(df)))


def convert_quarter_to_number(quarter_str):
    year, q = quarter_str.split('Q')
    return int(year) + (int(q) - 1) * 0.25


def plot_chart(df, x_col, chart_type="line", x_order=None):
    st.subheader("📈 Custom Charts")

    df = df.copy()
    if x_order:
        order_map = {label: i for i, label in enumerate(x_order)}
        df['X_Num'] = df[x_col].map(order_map)
    else:
        df['X_Num'] = convert_x_to_numeric(df, x_col)

    metrics = [
        ("Median_Price", "Median Price"),
        ("Median_Days", "Median Days on Market"),
        ("Count", "Number of Properties")
    ]

    for y_col, title in metrics:
        st.markdown(f"### {title}")

        encodings = {
            'x': alt.X(f'{x_col}:N', title='Period', sort=x_order),
            'y': alt.Y(f'{y_col}:Q', title=title),
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

        # Add trend line
        trend = alt.Chart(df).transform_regression(
            'X_Num', y_col
        ).mark_line(color='red').encode(
            x=alt.X('X_Num:Q', axis=None),  # 👈 Hide numeric axis
            y=alt.Y(f'{y_col}:Q')
        )

        final_chart = (base + trend).properties(
            width=800,
            height=300
        )

        st.altair_chart(final_chart, use_container_width=True)

        # Regression formula with safe fallback
        x = df['X_Num'].values
        y = df[y_col].values

        if len(df) > 1 and not np.isnan(x).any() and not np.isnan(y).any():
            try:
                a, b = np.polyfit(x, y, deg=1)
                st.markdown(f"**Regression Line Equation:**  \n`y = {a:.2f}x + {b:.2f}`")
            except np.linalg.LinAlgError:
                st.warning("⚠️ Regression failed: numerical issue (SVD did not converge).")
        else:
            st.info("Not enough clean data points to calculate regression equation.")

        st.markdown("---")


def plot_summary_table(df, x_col):
    st.subheader("📌 Summary Table")
    summary_df = df.rename(columns={
        x_col: 'Period',
        'Median_Price': 'Median Price',
        'Median_Days': 'Median Days on Market',
        'Count': 'Number of Properties'
    })
    st.dataframe(summary_df)

def plot_combo_chart_with_table(df, x_col, x_order=None):
    df = df.copy()  # Work on a copy of the DataFrame

    # 1️⃣ Transform Count & Median_Days into long format for grouped bars
    bar_df = df[[x_col, 'Count', 'Median_Days']].copy()
    bar_df = bar_df.melt(
        id_vars=[x_col],
        value_vars=['Count', 'Median_Days'],
        var_name='Metric',
        value_name='Value'
    )

    # 2️⃣ Base X axis
    base_x = alt.X(f'{x_col}:N', sort=x_order, title="Period")

    # 3️⃣ Line chart for Median_Price (blue, no legend)
    base_line = alt.Chart(df).encode(x=base_x)
    line_price = base_line.mark_line(point=True, color='steelblue').encode(
        y=alt.Y('Median_Price:Q',
                title='Median Sale $',
                axis=alt.Axis(titleColor='steelblue')),
        tooltip=['Median_Price']
    )
    price_text = base_line.mark_text(
        align='center', dy=-15, fontSize=12, color='steelblue'
    ).encode(
        y=alt.Y('Median_Price:Q', axis=None),
        text=alt.Text('Median_Price:Q', format=",.0f"),
        color=alt.value('steelblue')
    )

    # 4️⃣ Grouped bars for Count & Median_Days
    bar = alt.Chart(bar_df).mark_bar(opacity=0.75).encode(
        x=base_x,
        y=alt.Y('Value:Q',
                title='Count / Median Days',
                axis=alt.Axis(titleColor='orange', orient="left")),
        color=alt.Color('Metric:N',
                        scale=alt.Scale(domain=['Count', 'Median_Days'],
                                        range=['orange', 'green']),
                        legend=None),  # ❌ remove legend
        xOffset='Metric:N',
        tooltip=[x_col, 'Metric', 'Value']
    )

    # 5️⃣ Text labels for bars
    bar_text = alt.Chart(bar_df).mark_text(
        align='center', dy=-10, dx=7, fontSize=12
    ).encode(
        x=base_x,
        y=alt.Y('Value:Q', axis=None),
        text=alt.Text('Value:Q'),
        color=alt.Color('Metric:N',
                        scale=alt.Scale(domain=['Count', 'Median_Days'],
                                        range=['orange', 'green'])),
        xOffset='Metric:N'
    )

    # 6️⃣ Combine all layers
    chart = alt.layer(
        bar, bar_text,
        line_price, price_text
    ).resolve_scale(
        y='independent'
    ).properties(width=800, height=400)

    # 7️⃣ Show chart
    st.altair_chart(chart, use_container_width=True)

    # 8️⃣ Transposed table
    table_df = df[[x_col, 'Median_Price', 'Count', 'Median_Days']].copy()
    table_df = table_df.set_index(x_col).T
    table_df.index = ['Median Sale $', 'Count', 'Median Days on Market']
    st.dataframe(table_df, use_container_width=True)

    #  9️⃣ Custom legend (below the chart)
    st.markdown("🟧 **Orange Bar = Count**  🟩 **Green Bar = Median Days on Market**  🔵 **Blue Line = Median Sale Price**")


def plot_individual_scatter(df):
    # 🔵 Plot base scatter chart
    base = alt.Chart(df).mark_circle(size=60, opacity=0.6).encode(
        x=alt.X('Closed_Date:T', title="Closed Date"),
        y=alt.Y('Sold_Price:Q', title="Sold Price"),
        tooltip=['MLS_Number', 'Sold_Price', 'Contract_Date', 'Status']
    )

    # 🔴 Altair regression trend line (visual only)
    trend = alt.Chart(df).transform_regression(
        'Closed_Date', 'Sold_Price'
    ).mark_line(color='red').encode(
        x='Closed_Date:T',
        y='Sold_Price:Q'
    )

    chart = (base + trend).properties(
        width=800,
        height=400
    )

    st.altair_chart(chart, use_container_width=True)

    # 🧠 Regression: Use days since min date as x-axis
    df['Closed_Day'] = df['Closed_Date'].dt.date
    min_day = df['Closed_Day'].min()
    df['Days_Since_Min'] = (pd.to_datetime(df['Closed_Day']) - pd.to_datetime(min_day)).dt.days

    x = df['Days_Since_Min'].values
    y = df['Sold_Price'].values

    if len(x) > 1:
        a, b = np.polyfit(x, y, deg=1)
        st.markdown(f"**Regression Line Equation:**  \n`y = {a:.2f} * days_since_start + {b:.2f}`")
        st.caption(f"↳ Based on days since {min_day}, unit: dollars/day")

        # ✅ Add intuitive interpretation of slope
        if abs(a) >= 1:
            st.markdown(
                f"That means: for every additional day, the predicted sale price changes by approximately "
                f"<span style='color:red;'>${a:,.2f}</span>.",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"That means: for every additional day, the predicted sale price changes slightly by "
                f"<span style='color:red;'>${a:,.2f}</span>.",
                unsafe_allow_html=True
            )


