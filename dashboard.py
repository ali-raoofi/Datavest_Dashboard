import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import arabic_reshaper
from bidi.algorithm import get_display
import jdatetime
import os

# ---- Utility Functions ----
def fix_farsi(text):
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

def get_fee_rate_by_tier(tier, horizon):
    fee_matrix = {
        "3 months": {"10-50": 2.0, "50-250": 1.8, "250-500": 1.5, "500-1000": 1.2, ">1000": 1.0},
        "6 months": {"10-50": 2.5, "50-250": 2.3, "250-500": 2.2, "500-1000": 2.0, ">1000": 1.8},
        "9 months": {"10-50": 3.0, "50-250": 2.8, "250-500": 2.7, "500-1000": 2.6, ">1000": 2.5},
        "1 year":   {"10-50": 3.5, "50-250": 3.3, "250-500": 3.1, "500-1000": 3.0, ">1000": 2.9},
    }
    return fee_matrix[horizon][tier]

def determine_tier(investment_million):
    if investment_million <= 50:
        return "10-50"
    elif investment_million <= 250:
        return "50-250"
    elif investment_million <= 500:
        return "250-500"
    elif investment_million <= 1000:
        return "500-1000"
    else:
        return ">1000"

# ---- Page Config & Header ----
st.set_page_config(layout="wide")
st.markdown("""
    <h1 style='text-align: center; color: #BFA46F; font-weight: bold;'>DataVest Wealth Management Dashboard</h1>
""", unsafe_allow_html=True)

# ---- Sidebar: User Inputs ----
st.sidebar.header("Dashboard Settings")
if os.path.exists("400.png"):
    st.sidebar.image("400.png", width=270)
chart_investment_million = st.sidebar.number_input("Initial Investment (Million Toman)", value=100)
chart_investment = chart_investment_million * 1_00_000 * 10
period = st.sidebar.selectbox("Investment Horizon", ["1 month", "3 months", "6 months", "1 year", "2 years", "3 years"])
weeks_map = {"1 month": 4, "3 months": 13, "6 months": 26, "1 year": 52, "2 years": 104, "3 years": 156}
weeks = weeks_map[period]

# ---- Load and Prepare Data ----
df = pd.read_csv("compare_ret.csv", parse_dates=True, index_col=0)
df_period = df.tail(weeks)
wealth_df = df_period / df_period.iloc[0] * chart_investment

# Convert Gregorian dates to Shamsi (Persian)
shamsi_dates = [jdatetime.date.fromgregorian(date=d.date()).strftime('%Y/%m/%d') for d in wealth_df.index]
wealth_df.index = shamsi_dates

# Load R.csv if exists
if os.path.exists("R.csv"):
    r_full = pd.read_csv("R.csv", index_col=0, header=None)
    r_df = r_full.tail(len(wealth_df)).copy()
    r_df.columns = [f"fund_{i+1}" for i in range(r_df.shape[1])]
    r_df.index = wealth_df.index


# Assign fixed colors to competitors
competitors = wealth_df.columns.tolist()
color_palette = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3']
color_dict = dict(zip(competitors, color_palette))

# ---- Tabs Layout ----
tabs = st.tabs(["Wealth Chart", "Cumulative Return", "Data Table", "Fee Calculator"])

# ---- Tab 1: Wealth Index Chart ----
with tabs[0]:
    st.subheader("Wealth Index Comparison")
    fig_line = go.Figure()
    for col in wealth_df.columns:
        fig_line.add_trace(go.Scatter(
            x=wealth_df.index,
            y=wealth_df[col],
            mode='lines+markers',
            name=fix_farsi(col),
            line=dict(color=color_dict[col])
        ))

    fig_line.update_layout(
        title="Wealth Index Over Time",
        xaxis_title="Date (Shamsi)",
        yaxis_title="Wealth (Rial)",
        font=dict(family="Vazir, Tahoma, Arial", size=16),
        hovermode="x unified"
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # Ribbon Racing Chart
    st.subheader("Ranking Over Time (Race Chart)")
    ranking = df_period.rank(axis=1, ascending=False)
    race_data = ranking.reset_index().melt(id_vars='index', var_name='Competitor', value_name='Rank')
    race_data['Week'] = race_data['index'].apply(lambda d: jdatetime.date.fromgregorian(date=pd.to_datetime(d).date()).strftime('%Y/%m/%d'))
    st.plotly_chart(
        go.Figure(
            data=[go.Scatter(
                x=race_data[race_data['Competitor'] == c]['Week'],
                y=race_data[race_data['Competitor'] == c]['Rank'],
                mode='lines+markers',
                name=fix_farsi(c),
                line=dict(color=color_dict[c])
            ) for c in race_data['Competitor'].unique()],
            layout=go.Layout(
                yaxis=dict(autorange='reversed', title='Rank'),
                title='Weekly Competitor Rankings',
                font=dict(size=14)
            )
        ),
        use_container_width=True
    )

# ---- Tab 2: Cumulative Return ----
with tabs[1]:
    st.subheader("Cumulative Return")
    final_returns = (df_period.iloc[-1] / df_period.iloc[0]) - 1
    final_returns_percent = final_returns * 100

    fig_bar = go.Figure(data=[
        go.Bar(
            x=[fix_farsi(col) for col in final_returns_percent.index],
            y=final_returns_percent.values,
            text=[f"{val:.2f}%" for val in final_returns_percent.values],
            textposition='auto',
            marker_color=[color_dict[col] for col in final_returns_percent.index]
        )
    ])

    fig_bar.update_layout(
        title="End-of-Period Cumulative Return",
        yaxis_title="Return (%)",
        font=dict(family="Vazir, Tahoma, Arial", size=16)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ---- Tab 3: Data Table ----
with tabs[2]:
    if 'r_df' in locals():
        st.subheader("Investment Allocation by Week")
        st.dataframe(r_df)

    st.subheader("Underlying Data")
    st.dataframe(wealth_df.round(0).astype(int))

# ---- Tab 4: Fee Calculator ----
with tabs[3]:
    st.subheader("Fee Calculator")

    fee_investment_million = st.number_input("Enter Investment Amount (Million Toman)", value=100, key="fee_input")
    fee_investment = fee_investment_million * 1_00_000 * 10

    fee_horizon = st.selectbox("Select Investment Horizon", ["3 months", "6 months", "9 months", "1 year"])
    tier = determine_tier(fee_investment_million)
    base_rate = get_fee_rate_by_tier(tier, fee_horizon)

    num_installments = 1
    if fee_horizon in ["6 months", "9 months", "1 year"]:
        if tier == "250-500":
            num_installments = 2
        elif tier in ["500-1000", ">1000"]:
            num_installments = 3

    fee_rial = fee_investment * base_rate / 100

    st.markdown(f"### Investment: {fee_investment:,.0f} Toman")
    st.markdown(f"### Fee Rate: {base_rate:.2f}%")
    st.markdown(f"### Total Fee: {fee_rial:,.0f} Toman")

    if num_installments > 1:
        surcharge = fee_rial * 0.05
        total_with_surcharge = fee_rial + surcharge
        each = total_with_surcharge / num_installments
        st.markdown(f"### Payment Plan: {num_installments} Installments of {each:,.0f} Toman Each")

    # Monthly Fee Comparison
    months_map = {"3 months": 3, "6 months": 6, "9 months": 9, "1 year": 12}
    reference_rate = get_fee_rate_by_tier(tier, "3 months")
    reference_monthly_fee = (reference_rate / 100) * fee_investment / 3
    current_months = months_map[fee_horizon]
    current_monthly_fee = (base_rate / 100) * fee_investment / current_months

    if fee_horizon != "3 months":
        saving = reference_monthly_fee - current_monthly_fee
        saving_percent = (saving / reference_monthly_fee) * 100

        st.markdown("---")
        st.success(f"💡 **Monthly Fee:** {current_monthly_fee:,.0f} Toman vs {reference_monthly_fee:,.0f} in 3-month plan")
        st.success(f"🎁 Save **{saving:,.0f} Toman/month** ({saving_percent:.1f}% less per month) with **{fee_horizon}** plan.")
