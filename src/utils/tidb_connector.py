import pymysql
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class TiDBConnector:
    """Singleton class for TiDB database connection."""
    
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TiDBConnector, cls).__new__(cls)
        return cls._instance
    
    def get_connection(self):
        """Get the database connection (create if doesn't exist)."""
        if self._connection is None or not self._connection.open:
            self._connection = pymysql.connect(
                host=os.getenv("TIDB_HOST"),
                port=int(os.getenv("TIDB_PORT", "4000")),
                user=os.getenv("TIDB_USER"),
                password=os.getenv("TIDB_PASSWORD"),
                database=os.getenv("TIDB_DATABASE", "test"),
                ssl_verify_cert=True,
                ssl_verify_identity=True,
                ssl_ca=os.getenv("TIDB_SSL_CA", "/home/deep/Desktop/work/web/hackathon/src/utils/isrgrootx1.pem")
            )
        return self._connection
    
    def close(self):
        """Close the connection if it exists."""
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None

# Helper function to get the singleton instance
def get_db():
    return TiDBConnector().get_connection()

def execute_query(sql, params=None):
    """
    Execute a query and return the results as a dictionary.
    
    Args:
        sql (str): SQL query to execute
        params (tuple, optional): Parameters for the SQL query
        
    Returns:
        dict: Dictionary containing results and count
    """
    connection = get_db()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            # Convert results to list of dicts (if needed)
            result_list = [dict(row) for row in results]
            
            return {
                "count": len(result_list),
                "results": result_list
            }
    except Exception as e:
        return {"error": f"Error executing query: {str(e)}"}