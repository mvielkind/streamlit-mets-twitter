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


roster = [
    "Francisco Lindor",
    "Pete Alonso",
    "Max Scherzer",
    "Jacob deGrom",
    "Buck Showalter",
    "Steve Cohen",
    "Tomas Nido",
    "Carlos Carrasco",
    "Dom Smith",
    "Brandon Nimmo",
    "Mark Canha",
    "Luis Guillorme",
    "James McCann",
    "Starling Marte",
    "Eduardo Escobar",
    "Jeff McNeil",
    "Tylor Megill",
    "Chris Bassitt",
    "Edwin Diaz",
    "Nick Plummer",
    "Taijuan Walker",
    "Adam Ottavino",
    "David Peterson",
    "Drew Smith",
    "J. D. Davis",
    "Trevor Williams",
    "Adonis Medina",
    "Seth Lugo",
    "Patrick Mazeika",
    "Trevor May",
    "Chasen Shreve",
    "Francisco Alvarez",
    "Tommy Hunter",
    "Yoan Lopez",
    "Joely Rodriguez",
    "Billy Eppler"
]


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

    def player_sentiment(self, start_date):
        """Aggregate sentiment for players on Mets Twitter."""
        query = {
            "size": 0,
            "query": {
                "range": {
                    "created_at": {
                        "gte": start_date
                    }
                }
            },
            "aggs": {
                "player_buckets": {
                    "composite": {
                        "sources": [
                            {"player": {"terms": {"field": "player_entities"}}},
                            {"sentiment": {"terms": {"field": "sentiment.label"}}}
                        ],
                        "size": 10000
                    }
                }
            }
        }

        response = self.query(query)
        data = response.json()
        buckets = data["aggregations"]["player_buckets"]["buckets"]
        df = pd.json_normalize(buckets)
        df = df[df["key.player"].isin(roster)]

        data = df.pivot_table(
            values="doc_count",
            index="key.player",
            columns="key.sentiment",
            fill_value=0
        )

        data["Overall Sentiment"] = data["POS"] - data["NEG"]

        return data

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
        }

    def sentiment_history(self, start_date):
        """Get the sentiment for the day."""
        query = {
            "size": 0,
            "query": {
                "range": {
                    "created_at": {
                        "gte": start_date,
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
        data["rolling_POS"] = data["POS"].rolling(10, min_periods=1).sum()
        data["rolling_NEG"] = data["NEG"].rolling(10, min_periods=1).sum()
        data["rolling_sentiment"] = data["rolling_POS"] / (data["rolling_POS"] + data["rolling_NEG"])
        data["rolling_sentiment"].fillna(0, inplace=True)
        data.index.names = ["index"]

        return data
