import datetime
import streamlit as st
from analytics import MetsTwitter
import charts
import pytz

mt = MetsTwitter()

st.set_page_config(
    page_title="#MetsTwitter Feels"
)

st.title("#MetsTwitter Mood")
st.markdown("How's #MetsTwitter feeling today? Here's a real-ish time dashboard keeping a pulse on all the highs and "
            "lows that define #MetsTwitter!")

sentiment_today = mt.sentiment_window("now-24h")
st.markdown(f"### Current Mood: {sentiment_today['score']}")

start_date = st.date_input(
    label="Pick starting date for fan sentiment.",
    value=datetime.datetime.now(tz=pytz.timezone("US/Eastern")).date(),
    min_value=datetime.date(2022, 6, 17),
    max_value=datetime.datetime.now(tz=pytz.timezone("US/Eastern")).date()
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

# Show table of player sentiment.
st.subheader("Twitter Player Sentiment (last 24 hours)")

st.markdown("Where possible players are extracted from tweets. Players are ranked based on the ratio of "
            "positive to negative tweets.")

st.markdown("#### Top Player Sentiments")

player_sentiment = mt.player_sentiment()
player_table_1, player_table_2, player_table_3 = st.columns(3)
top_3 = player_sentiment.sort_values("Overall Sentiment", ascending=False)[:3]
with player_table_1:
    st.markdown("### 🥇")
    st.markdown(f"### {top_3.iloc[0].name}")

with player_table_2:
    st.markdown("### 🥈")
    st.markdown(f"### {top_3.iloc[1].name}")

with player_table_3:
    st.markdown("### 🥉")
    st.markdown(f"### {top_3.iloc[2].name}")

with st.expander("Full Player Sentiment Rankings..."):
    player_sentiment["Rank"] = player_sentiment["Overall Sentiment"].rank(
        method="min",
        ascending=False
    ).astype(int)
    st.table(player_sentiment.sort_values("Overall Sentiment", ascending=False)[["Rank"]])

# A note about the data.
st.subheader("Let's Get Nerdy 🤓")

with st.expander("View Technical Notes..."):
    st.markdown("Thank you for checking out my dashboard! The purpose is to track the mood of Mets Twitter. The data is "
                "extracted from the Twitter API using the filtered stream. The stream is filtered for tweets where the "
                "Mets are mentioned or the #LGM hashtag is used. The intention is to get a pulse on what's happening "
                "in the Mets Twitter universe. Tweets from other fanbases talking about the Mets are still being read. "
                "I'm working on identifying such tweets to get a more accurate sentiment of the New York Mets fan base. "
                "Additionally, the tweets represented here are just a sample of the total Twitter activity.")

    st.markdown("One problem I faced was keeping up the with stream of tweets, especially given the variability in tweet "
                "volume (large spikes during games). Originally I naively tried to run the NLP models against each tweet "
                "as they were received. Over time the processing was creating a backlog of tweets coming from the stream. "
                "To keep up with the tweets being received I separated reading the stream and processing the tweets into "
                "separate processes. When the stream is read each tweet is written to an Elastic index. A process was "
                "scheduled every minute to retrieve new documents from the database. The NLP models process the new "
                "documents in a batch and their entries updated. The entire process results in less than 2 minutes of "
                "latency between when the tweet is received and when it's represented in the dashboard. And it all runs on "
                "a small EC2 machine!")

    st.markdown("To measure sentiment the Huggingface [bertweet-base-sentiment-analysis](https://huggingface.co/finiteautomata/bertweet-base-sentiment-analysis) "
                "model is used. Reviewing tweets coming from the stream the model works reasonably well out-of-the-box."
                "Sports-related tweets can be dripping in sarcasm that the base model might not pickup. A future improvement "
                "could be fine-tuning the sentiment model to be specific to the tweets I'm using.")

    st.markdown("A custom NER model was trained using [spaCy](https://spacy.io/). The model was trained on a sample of "
                "tweets to extract player names. Right now the model has an F-Score of 0.81. The model is updated daily with "
                "tweets from the previous day.")

    st.markdown("Have any ideas for what you'd like to see? Let me know on [Twitter](https://twitter.com/MatthewVielkind)! "
                "I am working on a few more features to incorporate, but always open to new ideas!")
