import altair as alt
import pandas as pd
from statsmodels.nonparametric.smoothers_lowess import lowess


def time_series_chart(data):
    """Build the time series chart."""

    x = range(len(data))
    y = data["rolling_sentiment"].values

    new_data = pd.DataFrame(
        lowess(exog=x, endog=y, frac=0.02),
        columns=["index", "net_sentiment"]
    )
    new_data["time"] = data.index

    chart = alt.layer(
        alt.Chart().mark_line(),
        alt.Chart().mark_line().encode(
            color=alt.Color('is_neg:N', legend=None),
        ),
        data=new_data,
        title="#MetsTwitter Sentiment"
    ).transform_calculate(
        is_neg="datum.net_sentiment<0.5"
    ).encode(
        x=alt.X(
            "time:T",
            axis=alt.Axis(grid=False, title="")
        ),
        y=alt.Y(
            'net_sentiment:Q',
            impute={'value': None},
            axis=alt.Axis(labels=False, grid=False, title=""),
            scale=alt.Scale(domain=[0, 1.05])
        )
    )

    line = alt.Chart(pd.DataFrame({'y': [0.5]})).mark_rule().encode(y='y')

    return line + chart


def pos_neg_bar_chart(data: pd.DataFrame):
    """Bar chart allows negative numbers."""

    data.reset_index(inplace=True)
    cht = alt.Chart(data).mark_bar().encode(
        x=alt.X(
            "monthdate(index):O",
            axis=alt.Axis(grid=False, title="")
        ),
        y=alt.Y(
            "rolling_sentiment:Q",
            impute={'value': None},
            axis=alt.Axis(labels=False, grid=False, title=""),
            scale=alt.Scale(domain=[-1.05, 1.05])
        ),
        color=alt.condition(
            alt.datum.rolling_sentiment > 0,
            alt.value("steelblue"),  # The positive color
            alt.value("orange")  # The negative color
        )
    )

    line = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule().encode(y='y')

    return line + cht


def bar_chart(data):
    """Build a simple bar chart."""
    data["TOTAL"] = data["POS"] + data["NEG"]
    data["time"] = data.index
    chart = alt.Chart(data, title="# of Tweets").mark_bar().encode(
        x=alt.X(
            "time:T",
            axis=alt.Axis(grid=False, title="")
        ),
        y=alt.Y(
            'TOTAL:Q',
            impute={'value': None},
            axis=alt.Axis(labels=False, grid=False, title="")
        )
    )

    return chart
