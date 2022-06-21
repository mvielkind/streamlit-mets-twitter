import datetime
import streamlit as st
from analytics import MetsTwitter
import charts

mt = MetsTwitter()

st.title("#MetsTwitter Mood")
st.markdown("How's #MetsTwitter feeling today? Here's a real-ish time dashboard keeping a pulse on all the highs and "
            "lows that define #MetsTwitter!")

sentiment_today = mt.sentiment_window("now-1d")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Previous 7 Days",
        value=mt.sentiment_window("now-7d")["score"]
    )

with col2:
    st.metric(
        label="Last 24 Hours",
        value=sentiment_today["score"]
    )

with col3:
    # last_hour_sentiment = sentiment_trend.tail(60)["net_sentiment"].sum()
    # if last_hour_sentiment > 0:
    #     last_hour_sentiment = f"+{str(last_hour_sentiment)}"
    st.metric(
        label="Previous Hour",
        value=mt.sentiment_window("now-1h")["score"]
    )


# st.line_chart(
#     data=sentiment_trend["net_sentiment"]
# )

with st.sidebar:
    start_date = st.date_input(
        label="Pick a starting date.",
        value=datetime.datetime.now().date(),
        min_value=datetime.date(2022, 6, 17),
        max_value=datetime.datetime.now().date()
    )

sentiment_trend = mt.sentiment_history(start_date)

st.altair_chart(
    altair_chart=charts.time_series_chart(sentiment_trend),
    use_container_width=True
)

st.altair_chart(
    altair_chart=charts.bar_chart(sentiment_trend),
    use_container_width=True
)