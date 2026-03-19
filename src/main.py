from extract import extract_data
from transform import transform_data
from load import load_data

def run_pipeline():
    df = extract_data("data/raw_jobs.csv")
    df_clean = transform_data(df)
    load_data(df_clean, "outputs/jobs.db")
    print("ETL pipeline completed successfully!")

if __name__ == "__main__":
    run_pipeline()