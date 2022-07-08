import altair as alt
import pandas as pd
from statsmodels.nonparametric.smoothers_lowess import lowess


date_tick_freq = {
    "Last 12 Hours": "hour",
    "Last 24 Hours": "hour",
    "Last 7 Days": "day",
    "Season": "week"
}


def time_series_chart(data, period):
    """Build the time series chart."""

    x = range(len(data))
    y = data["rolling_sentiment"].values

    new_data = pd.DataFrame(
        lowess(exog=x, endog=y, frac=0.03),
        columns=["index", "rolling_sentiment"]
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
        is_neg="datum.rolling_sentiment<0.5"
    ).encode(
        x=alt.X(
            "time:T",
            axis=alt.Axis(
                grid=False,
                title="",
                tickCount=date_tick_freq[period]
            )
        ),
        y=alt.Y(
            'rolling_sentiment:Q',
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
            "monthdate(index):T",
            axis=alt.Axis(grid=False, title="", tickCount=alt.TimeIntervalStep(
                alt.TimeInterval("day"),
                step=2
            ))
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


def bar_chart(data, period):
    """Build a simple bar chart."""
    data["TOTAL"] = data["POS"] + data["NEG"]
    data["time"] = data.index
    chart = alt.Chart(data, title="# of Tweets").mark_bar().encode(
        x=alt.X(
            "time:T",
            axis=alt.Axis(grid=False, title="", tickCount=date_tick_freq[period])
        ),
        y=alt.Y(
            'TOTAL:Q',
            impute={'value': None},
            axis=alt.Axis(labels=False, grid=False, title="")
        )
    )

    return chart
