from utils.data_processing import main as process_data

def upload_data():
    """Upload data to TiDB."""
    print("Starting data upload to TiDB...")
    process_data()
    print("Data upload completed.")

if __name__ == "__main__":
    upload_data()
