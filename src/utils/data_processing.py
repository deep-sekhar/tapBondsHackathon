import pandas as pd
import json
import pymysql
import os
from datetime import datetime
from dotenv import load_dotenv
from utils.tidb_connector import get_db

def create_tables(connection):
    """Create tables in TiDB if they don't exist."""
    cursor = connection.cursor()
    
    # Bond Details table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bond_details (
        id VARCHAR(255) PRIMARY KEY,
        created_at VARCHAR(50) DEFAULT NULL,
        updated_at VARCHAR(50) DEFAULT NULL,
        isin VARCHAR(50) DEFAULT NULL,
        company_name VARCHAR(255) DEFAULT NULL,
        issue_size DECIMAL(20, 2) DEFAULT NULL,
        allotment_date DATE DEFAULT NULL,
        maturity_date DATE DEFAULT NULL,
        issuer_details MEDIUMTEXT DEFAULT NULL,
        instrument_details MEDIUMTEXT DEFAULT NULL,
        coupon_details MEDIUMTEXT DEFAULT NULL,
        redemption_details MEDIUMTEXT DEFAULT NULL,
        credit_rating_details MEDIUMTEXT DEFAULT NULL,
        listing_details MEDIUMTEXT DEFAULT NULL,
        key_contacts_details MEDIUMTEXT DEFAULT NULL,
        key_documents_details MEDIUMTEXT DEFAULT NULL
    )
    """)
    
    # Cashflows table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cashflows (
        id VARCHAR(255) PRIMARY KEY,
        isin VARCHAR(50) DEFAULT NULL,
        cash_flow_date DATE DEFAULT NULL,
        cash_flow_amount DECIMAL(20, 4) DEFAULT NULL,
        record_date DATE DEFAULT NULL,
        principal_amount DECIMAL(20, 4) DEFAULT NULL,
        interest_amount DECIMAL(20, 4) DEFAULT NULL,
        tds_amount DECIMAL(20, 4) DEFAULT NULL,
        remaining_principal DECIMAL(20, 4) DEFAULT NULL,
        state VARCHAR(50) DEFAULT NULL,
        created_at VARCHAR(50) DEFAULT NULL,
        updated_at VARCHAR(50) DEFAULT NULL,
        INDEX (isin)
    )
    """)
    
    # Company Insights table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_insights (
        id VARCHAR(255) PRIMARY KEY,
        created_at VARCHAR(50) DEFAULT NULL,
        updated_at VARCHAR(50) DEFAULT NULL,
        company_name VARCHAR(255) DEFAULT NULL,
        company_industry VARCHAR(255) DEFAULT NULL,
        description TEXT DEFAULT NULL,
        key_metrics TEXT DEFAULT NULL,
        income_statement TEXT DEFAULT NULL,
        balance_sheet TEXT DEFAULT NULL,
        cashflow TEXT DEFAULT NULL,
        lenders_profile TEXT DEFAULT NULL,
        comparison TEXT DEFAULT NULL,
        borrowers_profile TEXT DEFAULT NULL,
        shareholding_profile TEXT DEFAULT NULL,
        pros TEXT DEFAULT NULL,
        cons TEXT DEFAULT NULL,
        key_personnel TEXT DEFAULT NULL,
        news_and_events TEXT DEFAULT NULL,
        INDEX (company_name)
    )
    """)
    
    connection.commit()
    cursor.close()

def load_excel_data(file_path):
    """Load data from Excel file."""
    print(f"Loading data from {file_path}...")
    return pd.read_excel(file_path)

def process_json_columns(df):
    """Process JSON columns in the dataframe."""
    for column in df.columns:
        if df[column].dtype == 'object':
            try:
                df[column] = df[column].apply(
                    lambda x: json.dumps(json.loads(x)) if isinstance(x, str) and x.strip().startswith('{') else x
                )
            except Exception as e:
                print(f"Error processing column {column}: {e}")
    return df

def insert_bond_details(connection, df, batch_size=50):
    """Insert bond details data into TiDB in batches."""
    cursor = connection.cursor()
    
    # Process the dataframe
    df = process_json_columns(df)
    
    # Clear existing data
    cursor.execute("TRUNCATE TABLE bond_details")
    connection.commit()

    # Replace NaN values with None (which becomes NULL in SQL)
    df = df.replace({float('nan'): None, 'nan': None})
    df = df.where(pd.notnull(df), None)
    
    total_records = len(df)
    count = 0
    next_log_threshold = 1000
    
    for batch_num, start in enumerate(range(0, total_records, batch_size), start=1):
        batch = df.iloc[start:start+batch_size]
        params = []
        for _, row in batch.iterrows():
            # Convert date columns with error handling
            allotment_date = None
            if pd.notna(row['allotment_date']):
                try:
                    # Explicitly specify dayfirst=True for DD-MM-YYYY format
                    allotment_date = pd.to_datetime(row['allotment_date'], dayfirst=True).strftime('%Y-%m-%d')
                except (ValueError, OverflowError, pd._libs.tslibs.np_datetime.OutOfBoundsDatetime) as e:
                    print(f"Warning: Invalid allotment_date '{row['allotment_date']}' for ISIN {row.get('isin', 'unknown')}")
            
            maturity_date = None
            if pd.notna(row['maturity_date']):
                try:
                    # Explicitly specify dayfirst=True for DD-MM-YYYY format
                    maturity_date = pd.to_datetime(row['maturity_date'], dayfirst=True).strftime('%Y-%m-%d')
                except (ValueError, OverflowError, pd._libs.tslibs.np_datetime.OutOfBoundsDatetime) as e:
                    print(f"Warning: Invalid maturity_date '{row['maturity_date']}' for ISIN {row.get('isin', 'unknown')}")
            
            # Handle JSON columns
            json_fields = {'issuer_details': None, 'instrument_details': None, 'coupon_details': None,
                          'redemption_details': None, 'credit_rating_details': None, 'listing_details': None,
                          'key_contacts_details': None, 'key_documents_details': None}
            
            for col in json_fields:
                if col in row and pd.notna(row[col]):
                    try:
                        # If it's a dict, convert to JSON string
                        if isinstance(row[col], dict):
                            json_str = json.dumps(row[col])
                        else:
                            json_str = str(row[col])
                            
                        # Check size and truncate if needed
                        max_size = 4000000  # ~4MB to be safe (MEDIUMTEXT limit is ~16MB)
                        if len(json_str) > max_size:
                            print(f"Warning: Truncating oversized {col} from {len(json_str)} bytes to {max_size} bytes for ISIN {row.get('isin', 'unknown')}")
                            json_fields[col] = json_str[:max_size] + " ... [truncated]"
                        else:
                            json_fields[col] = json_str
                    except Exception as json_error:
                        print(f"Error processing JSON column {col} for ISIN {row.get('isin', 'unknown')}: {str(json_error)}")
                        json_fields[col] = None
            
            params.append((
                row['id'], row['created_at'], row['updated_at'], row['isin'], row['company_name'], 
                row['issue_size'], allotment_date, maturity_date, row['issuer_details'], 
                row['instrument_details'], row['coupon_details'], row['redemption_details'], 
                row['credit_rating_details'], row['listing_details'], row['key_contacts_details'], 
                row['key_documents_details']
            ))
        
        try:
            cursor.executemany("""
            INSERT INTO bond_details 
            (id, created_at, updated_at, isin, company_name, issue_size, allotment_date, maturity_date,
             issuer_details, instrument_details, coupon_details, redemption_details, credit_rating_details,
             listing_details, key_contacts_details, key_documents_details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, params)
            connection.commit()
            
            count += len(batch)
            if count >= next_log_threshold:
                print(f"Completed {count} entries (batch number {batch_num})")
                next_log_threshold += 1000
                
        except Exception as e:
            print(f"Error in batch {batch_num}: {e}")
            connection.rollback()
    
    print(f"Inserted {total_records} bond details records")
    cursor.close()

def insert_cashflows(connection, df, batch_size=1000):
    """Insert cashflows data into TiDB in batches."""
    cursor = connection.cursor()
    
    # Clear existing data
    cursor.execute("TRUNCATE TABLE cashflows")
    connection.commit()

    # Replace NaN values with None (which becomes NULL in SQL)
    df = df.replace({float('nan'): None, 'nan': None})
    df = df.where(pd.notnull(df), None)
    
    total_records = len(df)
    for start in range(0, total_records, batch_size):
        batch = df.iloc[start:start+batch_size]
        params = []
        for _, row in batch.iterrows():
            cash_flow_date = pd.to_datetime(row['cash_flow_date']).strftime('%Y-%m-%d') if pd.notna(row['cash_flow_date']) else None
            record_date = pd.to_datetime(row['record_date']).strftime('%Y-%m-%d') if pd.notna(row['record_date']) else None
            params.append((
                row['id'], row['isin'], cash_flow_date, row['cash_flow_amount'], record_date,
                row['principal_amount'], row['interest_amount'], row['tds_amount'], row['remaining_principal'],
                row['state'], row['created_at'], row['updated_at']
            ))
        
        cursor.executemany("""
        INSERT INTO cashflows 
        (id, isin, cash_flow_date, cash_flow_amount, record_date, principal_amount, interest_amount,
         tds_amount, remaining_principal, state, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, params)
        connection.commit()
    
    print(f"Inserted {total_records} cashflow records")
    cursor.close()

def insert_company_insights(connection, df, batch_size=1000):
    """Insert company insights data into TiDB in batches."""
    cursor = connection.cursor()
    
    # Process the dataframe
    df = process_json_columns(df)
    
    # Clear existing data
    cursor.execute("TRUNCATE TABLE company_insights")
    connection.commit()

    # Replace NaN values with None (which becomes NULL in SQL)
    df = df.replace({float('nan'): None, 'nan': None})
    df = df.where(pd.notnull(df), None)
    
    total_records = len(df)
    for start in range(0, total_records, batch_size):
        batch = df.iloc[start:start+batch_size]
        params = []
        for _, row in batch.iterrows():
            for col in ['key_metrics', 'income_statement', 'balance_sheet', 'cashflow', 'lenders_profile',
                        'comparison', 'borrowers_profile', 'shareholding_profile', 'pros', 'cons', 'key_personnel']:
                if isinstance(row[col], (list, dict)):
                    row[col] = json.dumps(row[col])
                    
            params.append((
                row['id'], row['created_at'], row['updated_at'], row['company_name'], row['company_industry'],
                row['description'], row['key_metrics'], row['income_statement'], row['balance_sheet'],
                row['cashflow'], row['lenders_profile'], row['comparison'], row['borrowers_profile'],
                row['shareholding_profile'], row['pros'], row['cons'], row['key_personnel'], row['news_and_events']
            ))
        
        cursor.executemany("""
        INSERT INTO company_insights 
        (id, created_at, updated_at, company_name, company_industry, description, key_metrics,
         income_statement, balance_sheet, cashflow, lenders_profile, comparison, borrowers_profile,
         shareholding_profile, pros, cons, key_personnel, news_and_events)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, params)
        connection.commit()
    
    print(f"Inserted {total_records} company insight records")
    cursor.close()

def fetch_bond_by_isin(connection, isin):
    """Fetch bond details by ISIN."""
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM bond_details WHERE isin = %s", (isin,))
    result = cursor.fetchone()
    cursor.close()
    return result

def fetch_bonds_by_company(connection, company_name):
    """Fetch bonds by company name."""
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM bond_details WHERE company_name LIKE %s", (f"%{company_name}%",))
    results = cursor.fetchall()
    cursor.close()
    return results

def fetch_cashflows_by_isin(connection, isin):
    """Fetch cashflows by ISIN."""
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM cashflows WHERE isin = %s ORDER BY cash_flow_date", (isin,))
    results = cursor.fetchall()
    cursor.close()
    return results

def fetch_company_insight(connection, company_name):
    """Fetch company insight by company name."""
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM company_insights WHERE company_name LIKE %s", (f"%{company_name}%",))
    result = cursor.fetchone()
    cursor.close()
    return result

def main():
    """Main function to process all data files."""
    connection = get_db()
    
    try:
        # Create tables
        create_tables(connection)
        
        # Define data files along with their processors and batch sizes.
        # For CSV files, change the file extension accordingly.
        data_files = [
            {'file': '/home/deep/Desktop/work/web/hackathon/data/bonds_details.csv', 'processor': insert_bond_details, 'batch_size': 100},
            # {'file': '/home/deep/Desktop/work/web/hackathon/data/cashflows.csv', 'processor': insert_cashflows, 'batch_size': 1000},
            # {'file': '/home/deep/Desktop/work/web/hackathon/data/company_insights.csv', 'processor': insert_company_insights, 'batch_size': 1000}
        ]
        
        # Process each file
        for data_file in data_files:
            file_path = data_file['file']
            processor = data_file['processor']
            batch_size = data_file['batch_size']
            
            if os.path.exists(file_path):
                # Load data based on file extension
                if file_path.endswith('.csv'):
                    print(f"Loading data from {file_path}...")
                    df = pd.read_csv(file_path)
                else:
                    df = load_excel_data(file_path)
                
                # Process and insert data in batches
                processor(connection, df, batch_size)
            else:
                print(f"File not found: {file_path}")
        
        print("Data processing completed.")
    
    finally:
        connection.close()

if __name__ == "__main__":
    main()