import pandas as pd

def transform_data(df):
    df = df.drop_duplicates()
    df["salary"] = df["salary"].fillna("Unknown")
    df["location"] = df["location"].str.strip().str.lower()
    df["posted_date"] = pd.to_datetime(df["posted_date"])
    return df