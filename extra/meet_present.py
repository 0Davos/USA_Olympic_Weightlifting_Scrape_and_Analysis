'''
Presenting meet data, plotly

MOVE THIS TO FRONTEND REPO
'''
import pandas as pd
import numpy as np
import plotly.graph_objects as go



# bodyweight vs total, with multiple lines representing percentile (99th, 75th, 50th, 25th, 1st)
def mens_graph_bw_vs_total(meet_df, bin_size):
    # convert columns to numeric, just to be sure
    meet_df["Bodyweight"] = pd.to_numeric(meet_df["Bodyweight"], errors="coerce")
    meet_df["Total"] = pd.to_numeric(meet_df["Total"], errors="coerce")


    # Drop NaN
    meet_df = meet_df.dropna(subset=["Bodyweight", "Total"])

    # Filter bodyweight (e.g., only athletes <= 200 kg)
    male_df = meet_df[(meet_df["WC_Gender"] == "Men") & (meet_df["Bodyweight"] <= 200) & (meet_df['Bodyweight'] >= 20)]

    # Compute percentiles across bodyweight
    # We'll group by small bodyweight intervals (like _kg bands) to get smooth curves
    bw_step = bin_size
    male_df["bw_bin"] = (male_df["Bodyweight"] // bw_step) * bw_step

    percentiles = male_df.groupby("bw_bin")["Total"].quantile([0.25, 0.5, 0.75, 0.99]).unstack()

    # Make a figure
    fig = go.Figure()

    # Add percentile lines
    for p in [0.25, 0.5, 0.75, 0.99]:
        fig.add_trace(go.Scatter(
            x=percentiles.index,
            y=percentiles[p],
            mode='lines+markers',
            name=f'{int(p*100)}th Percentile'
        ))
    # Add formatting
    fig.update_layout(
        title="Olympic Weightlifting Totals by Bodyweight (Percentile, Men's)",
        xaxis_title="Bodyweight (kg)",
        yaxis_title="Total (kg)",
        template="plotly_dark",
        hovermode="x unified"
    )

    fig.show()
    return 0

def womens_graph_bw_vs_total(meet_df, bin_size):
    # convert columns to numeric, just to be sure
    meet_df["Bodyweight"] = pd.to_numeric(meet_df["Bodyweight"], errors="coerce")
    meet_df["Total"] = pd.to_numeric(meet_df["Total"], errors="coerce")


    # Drop NaN
    meet_df = meet_df.dropna(subset=["Bodyweight", "Total"])

    # Filter bodyweight (e.g., only athletes <= 200 kg)
    female_df = meet_df[(meet_df["WC_Gender"] == "Women") & (meet_df["Bodyweight"] <= 150) & (meet_df['Bodyweight'] >= 20)]

    # Compute percentiles across bodyweight
    # We'll group by small bodyweight intervals (like _kg bands) to get smooth curves
    bw_step = bin_size
    female_df["bw_bin"] = (female_df["Bodyweight"] // bw_step) * bw_step

    percentiles = female_df.groupby("bw_bin")["Total"].quantile([0.25, 0.5, 0.75, 0.99]).unstack()

    # Make a figure
    fig = go.Figure()

    # Add percentile lines
    for p in [0.25, 0.5, 0.75, 0.99]:
        fig.add_trace(go.Scatter(
            x=percentiles.index,
            y=percentiles[p],
            mode='lines+markers',
            name=f'{int(p*100)}th Percentile'
        ))
    # Add formatting
    fig.update_layout(
        title="Olympic Weightlifting Totals by Bodyweight (Percentile, Women's)",
        xaxis_title="Bodyweight (kg)",
        yaxis_title="Total (kg)",
        template="plotly_dark",
        hovermode="x unified"
    )

    fig.show()
    return 0


def graph_bw_vs_total_bins(meet_df):
    return 0

# count vs total, broken down to make a graph for each bodyweight
def graph_count_vs_total(bodyweight, meet_df):
    meet_df["Category"] == bodyweight
    return 0


# misses/makes by gender, # lift, bodyweight, etc
def misses_by_gender(df):
    return 0
def misses_by_lift_num(df):
    return 0
def misses_by_bodyweight(df):
    return 0

if __name__ == '__main__':
    df = pd.read_csv("meet_results_CLEANED.csv")

    mens_graph_bw_vs_total(df, bin_size=10)
    womens_graph_bw_vs_total(df, bin_size=10)

