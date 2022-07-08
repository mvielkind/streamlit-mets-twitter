import json
import random
import requests
import numpy as np
import streamlit as st
import pandas as pd
import pytz


ELASTIC_USER = st.secrets["ELASTIC_USER"]
ELASTIC_URL = st.secrets["ELASTIC_URL"]
ELASTIC_PASS = st.secrets["ELASTIC_PASS"]
ELASTIC_INDEX = st.secrets["ELASTIC_INDEX"]


moods = json.load(open("emoji_moods.json", "r"))


lookback_map = {
    "Last 12 Hours": {
        "date_lookback": "now-12h/h",
        "interval": "1m",
        "smooth_periods": 30
    },
    "Last 24 Hours": {
        "date_lookback": "now-24h/h",
        "interval": "1m",
        "smooth_periods": 30
    },
    "Last 7 Days": {
        "date_lookback": "now-168h/h",
        "interval": "15m",
        "smooth_periods": 4
    },
    "Season": {
        "date_lookback": "2022-06-20 00:00:00",
        "interval": "60m",
        "smooth_periods": 1
    }
}


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
    "J.D. Davis",
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
    "Billy Eppler",
    "Ender Inciarte",
    "Jake Reed"
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

    def player_sentiment(self, period: str):
        """Aggregate sentiment for players on Mets Twitter."""
        lookback_params = lookback_map[period]
        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"range": {
                            "created_at": {
                                "gte": lookback_params["date_lookback"]
                            }
                        }},
                    ],
                    "must_not": [
                        {"term": {"is_opposing_fan": "true"}}
                    ]
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
                "bool": {
                    "must": [
                        {"range": {
                            "created_at": {
                                "gte": _from,
                                "lt": "now"
                            }
                        }}
                    ],
                    "must_not": [
                        {"term": {"is_opposing_fan": "true"}}
                    ]
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

    def sentiment_history(self, period: str):
        """Get the sentiment for the day."""
        lookback_params = lookback_map[period]
        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"range": {
                            "created_at": {
                                "gte": lookback_params["date_lookback"],
                                "lt": "now"
                            }
                        }}
                    ],
                    "must_not": [
                        {"term": {"is_opposing_fan": "true"}}
                    ]
                }
            },
            "aggs": {
                "tweets_by_minute": {
                    "composite": {
                        "sources": [
                            {"created_at": {"date_histogram": {"field": "created_at", "fixed_interval": lookback_params["interval"]}}},
                            {"sentiment": {"terms": {"field": "sentiment.label"}}}
                        ],
                        "size": 5000
                    }
                }
            }
        }

        response = self.query(query)
        data = response.json()
        try:
            buckets = data["aggregations"]["tweets_by_minute"]["buckets"]
        except KeyError:
            print(data)
            raise KeyError("Error in Elastic response")
        df = pd.json_normalize(buckets)
        df["key.date"] = pd.to_datetime(df["key.created_at"], unit="ms")
        data = df.pivot_table(
            values="doc_count",
            index="key.date",
            columns="key.sentiment",
            fill_value=0
        )
        data["rolling_POS"] = data["POS"].rolling(lookback_params["smooth_periods"], min_periods=1).sum()
        data["rolling_NEG"] = data["NEG"].rolling(lookback_params["smooth_periods"], min_periods=1).sum()
        data["rolling_sentiment"] = data["rolling_POS"] / (data["rolling_POS"] + data["rolling_NEG"])
        data["rolling_sentiment"].fillna(0, inplace=True)
        data.index.names = ["index"]

        return data

    def player_history(self, player: str):
        """Daily history of player sentiment."""
        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"term": {"player_entities": player}}
                    ],
                    "must_not": [
                        {"term": {"is_opposing_fan": "true"}}
                    ]
                }
            },
            "aggs": {
                "daily_sentiment": {
                    "composite": {
                        "sources": [
                            {"date": {"date_histogram": {"field": "created_at", "calendar_interval": "1d"}}},
                            {"sentiment": {"terms": {"field": "sentiment.label"}}}
                        ],
                        "size": 5000
                    }
                }
            }
        }

        response = self.query(query)
        data = response.json()
        buckets = data["aggregations"]["daily_sentiment"]["buckets"]
        df = pd.json_normalize(buckets)
        df["key.date"] = pd.to_datetime(df["key.date"], unit="ms")
        tbl = df.pivot_table(
            values="doc_count",
            index="key.date",
            columns="key.sentiment",
            fill_value=0
        )
        # tbl.tz_localize(tz=pytz.timezone("US/Eastern"))
        tbl["rolling_sentiment"] = tbl["POS"] / (tbl["POS"] + tbl["NEG"])
        tbl.replace([np.inf, -np.inf], 0, inplace=True)
        tbl["rolling_sentiment"] = (tbl["rolling_sentiment"]-0.5) * 2
        tbl.index.names = ["index"]

        return tbl

