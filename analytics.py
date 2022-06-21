import json
import random
import requests
import streamlit as st
import pandas as pd


ELASTIC_USER = st.secrets["ELASTIC_USER"]
ELASTIC_URL = st.secrets["ELASTIC_URL"]
ELASTIC_PASS = st.secrets["ELASTIC_PASS"]
ELASTIC_INDEX = st.secrets["ELASTIC_INDEX"]


moods = json.load(open("emoji_moods.json", "r"))


class ElasticHelper:

    def __init__(self, url=ELASTIC_URL, index=ELASTIC_INDEX):
        self.url = url
        self.index = index

    def query(self, query):
        response = requests.post(
            url=f"https://{self.url}/{self.index}/_search",
            headers={'content-type': 'application/json', 'charset': 'UTF-8'},
            data=json.dumps(query),
            auth=(ELASTIC_USER, ELASTIC_PASS)
        )

        return response


class MetsTwitter(ElasticHelper):

    def current_sentiment(self):
        pass

    def sentiment_window(self, _from):
        query = {
            "size": 0,
            "query": {
                "range": {
                    "created_at": {
                        "gte": _from,
                        "lt": "now"
                    }
                }
            },
            "aggs": {
                "daily_sentiment": {
                    "terms": {"field": "sentiment.label"}
                }
            }
        }
        """Get the sentiment for the day."""

        response = self.query(query)
        data = response.json()
        buckets = data["aggregations"]["daily_sentiment"]["buckets"]

        sentiments = {b["key"]: b["doc_count"] for b in buckets}
        raw_score = sentiments["POS"] / (sentiments["POS"] + sentiments["NEG"])

        if raw_score >= 0.60:
            s = random.choice(moods["positive"])
        elif raw_score < 0.40:
            s = random.choice(moods["negative"])
        else:
            s = random.choice(moods["neutral"])

        return {
            "score": s
            # "score": round(raw_score * (1 - -1) - 1, 2)
        }

        # if sentiments["POS"] > sentiments["NEG"]:
            # return {
            #     "sentiment": "POS",
            #     "score": f'+{sentiments["POS"] - sentiments["NEG"]}'
            # }
        # elif sentiments["POS"] < sentiments["NEG"]:
        #     return {
        #         "sentiment": "NEG",
        #         "score": f'{sentiments["POS"] - sentiments["NEG"]}'
        #     }
        # else:
        #     return {
        #         "sentiment": "NEU",
        #         "score": '-'
        #     }

    def sentiment_history(self, start_date):
        """Get the sentiment for the day."""
        query = {
            "size": 0,
            "query": {
                "range": {
                    "created_at": {
                        "gte": f"{start_date} 00:00:00",
                        "lt": "now"
                    }
                }
            },
            "aggs": {
                "tweets_by_minute": {
                    "composite": {
                        "sources": [
                            {"created_at": {"date_histogram": {"field": "created_at", "fixed_interval": "1m"}}},
                            {"sentiment": {"terms": {"field": "sentiment.label"}}}
                        ],
                        "size": 10000
                    }
                }
            }
        }

        response = self.query(query)
        data = response.json()
        buckets = data["aggregations"]["tweets_by_minute"]["buckets"]
        df = pd.json_normalize(buckets)
        df["key.date"] = pd.to_datetime(df["key.created_at"], unit="ms")
        data = df.pivot_table(
            values="doc_count",
            index="key.date",
            columns="key.sentiment",
            fill_value=0
        )
        # data["net_sentiment"] = data["POS"] - data["NEG"]
        data["net_sentiment"] = data["POS"] / (data["POS"] + data["NEG"])
        data["net_sentiment"].fillna(0, inplace=True)
        data["rolling_POS"] = data["POS"].rolling(10, min_periods=1).sum()
        data["rolling_NEG"] = data["NEG"].rolling(10, min_periods=1).sum()
        data["rolling_sentiment"] = data["rolling_POS"] / (data["rolling_POS"] + data["rolling_NEG"])
        data["rolling"] = data["net_sentiment"].rolling(6, min_periods=1).sum()
        data["rolling_sentiment"].fillna(0, inplace=True)
        data.index.names = ["index"]

        return data
