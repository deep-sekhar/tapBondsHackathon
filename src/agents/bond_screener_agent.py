from langchain.agents import Tool
from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from src.utils.tidb_connector import execute_query
import json
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class BondScreenerAgent:
    def __init__(self, api_key=None):
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GAI_PS"),
            temperature=0
        )
        
        # Create master prompt
        template = """You are a Bond Screener Agent that helps users analyze companies that issue bonds.

        The company_insights table has these columns:
        - id (string): Unique identifier for the company record
        - created_at (string): Timestamp when the record was created
        - updated_at (string): Timestamp when the record was last updated
        - company_name (string): Name of the company
        - company_industry (string): Industry the company operates in
        - description (text): Detailed description of the company
        - key_metrics (JSON): Financial metrics like EPS, Current ratio, Debt/Equity, Debt/EBITDA, etc.
        - income_statement (JSON): Revenue, expenses, and profit information
        - balance_sheet (JSON): Assets, liabilities, and equity information
        - cashflow (JSON): Cash flow data including operating, investing, and financing activities
        - lenders_profile (JSON): Information about the company's lenders
        - comparison (JSON): Comparison with peer companies
        - borrowers_profile (JSON): Information about the company's borrowers
        - shareholding_profile (JSON): Information about the company's shareholders
        - pros (text): Positive aspects of the company
        - cons (text): Negative aspects or risks associated with the company
        - key_personnel (JSON): Information about key executives and management
        - news_and_events (text): Recent news and events related to the company
        
        You can filter companies using these criteria:
        - String fields (company_name, company_industry, etc.):
          - equals: Exact match (=)
          - contains: Partial match (LIKE %value%)
          
        - JSON fields (using JSON_EXTRACT):
          - key_metrics_contains: Search for specific metrics or values within the key_metrics JSON
          - income_statement_contains: Search within income statement data
          - balance_sheet_contains: Search within balance sheet data
          - cashflow_contains: Search within cashflow data
          - lenders_profile_contains: Search within lenders profile data
          - key_personnel_contains: Search for specific people or roles
          
        - Text fields (description, pros, cons, news_and_events):
          - description_contains: Search within company description
          - pros_contains: Search within company pros
          - cons_contains: Search within company cons
          - news_contains: Search within company news and events
        
        User query: {query}
        
        Your task is to:
        1. Determine what company information the user is asking for
        2. Construct an optimized SQL query that retrieves ONLY the necessary columns
        3. ALWAYS use LIMIT in your queries to avoid retrieving too much data
        4. Format the query as a JSON object with these fields:
           - table: The table to query (here "company_insights")
           - columns: Array of column names to retrieve
           - filters: Object with filter conditions
           - limit: Maximum number of results must be <= 5
        
        Example 1 - Company lookup:
        {{
            "table": "company_insights",
            "columns": ["company_name", "company_industry", "description", "key_metrics", "pros", "cons"],
            "filters": {{
                "company_name": "Navi Finserv"
            }},
            "limit": 1
        }}
        
        Example 2 - Industry search:
        {{
            "table": "company_insights",
            "columns": ["company_name", "company_industry", "key_metrics"],
            "filters": {{
                "company_industry": "Finance"
            }},
            "limit": 5
        }}
        
        Output the JSON query object only, nothing else.
        """
        
        self.prompt = PromptTemplate(template=template, input_variables=["query"])
        
        # Update to use newer style (avoid deprecation warning)
        from langchain_core.runnables import RunnableSequence
        self.chain = RunnableSequence(self.prompt, self.llm)
    
    def process_query(self, query):
        """Process a bond screener query and return a response."""
        try:
            # Get query JSON from LLM
            response = self.chain.invoke({"query": query})
            
            # Debug the response
            print(f"DEBUG - Response type: {type(response)}")
            
            # Extract content from response
            json_str = None
            if hasattr(response, "content"):
                json_str = response.content
            elif isinstance(response, dict) and "text" in response:
                json_str = response["text"]
            elif isinstance(response, str):
                json_str = response
            else:
                json_str = str(response)
            
            print(f"DEBUG - Extracted JSON: {json_str}")
            
            # Clean up the markdown code block formatting
            if json_str.startswith("```"):
                # Extract just the JSON part between the code block markers
                lines = json_str.split("\n")
                # Remove first line (```json) and last line (```
                clean_lines = lines[1:-1] if len(lines) > 2 else lines
                json_str = "\n".join(clean_lines)
            
            # Parse the JSON response
            query_params = json.loads(json_str)
            
            # Execute the optimized query
            result = self.execute_optimized_query(query_params)
            
            return result
        except Exception as e:
            return {"error": f"Error processing query: {str(e)}"}
    
    def execute_optimized_query(self, query_params):
        """Execute an optimized TiDB query for company_insights table."""
        try:
            # Extract parameters
            table = "company_insights"  # Ensure we're querying the correct table
            columns = query_params.get("columns", ["company_name", "company_industry"])
            filters = query_params.get("filters", {})
            limit = query_params.get("limit", 5)
            
            # Ensure limit is applied
            if not limit or limit > 100:
                limit = 5
            
            # Build column list for SQL
            sql_columns = columns
            
            # Build WHERE clause
            conditions = []
            params = []
            
            for key, value in filters.items():
                # String field exact matches
                if key == "company_name" and not key.endswith("_contains"):
                    conditions.append("company_name = %s")
                    params.append(value)
                elif key == "company_name_contains" or (key == "company_name" and key.endswith("_contains")):
                    conditions.append("company_name LIKE %s")
                    params.append(f"%{value}%")
                elif key == "company_industry" and not key.endswith("_contains"):
                    conditions.append("company_industry = %s")
                    params.append(value)
                elif key == "company_industry_contains" or (key == "company_industry" and key.endswith("_contains")):
                    conditions.append("company_industry LIKE %s")
                    params.append(f"%{value}%")
                
                # Text field contains searches
                elif key == "description_contains":
                    conditions.append("description LIKE %s")
                    params.append(f"%{value}%")
                elif key == "pros_contains":
                    conditions.append("pros LIKE %s")
                    params.append(f"%{value}%")
                elif key == "cons_contains":
                    conditions.append("cons LIKE %s")
                    params.append(f"%{value}%")
                elif key == "news_contains":
                    conditions.append("news_and_events LIKE %s")
                    params.append(f"%{value}%")
                
                # JSON field searches
                elif key == "key_metrics_contains":
                    conditions.append("key_metrics LIKE %s")
                    params.append(f"%{value}%")
                elif key == "income_statement_contains":
                    conditions.append("income_statement LIKE %s")
                    params.append(f"%{value}%")
                elif key == "balance_sheet_contains":
                    conditions.append("balance_sheet LIKE %s")
                    params.append(f"%{value}%")
                elif key == "cashflow_contains":
                    conditions.append("cashflow LIKE %s")
                    params.append(f"%{value}%")
                elif key == "lenders_profile_contains":
                    conditions.append("lenders_profile LIKE %s")
                    params.append(f"%{value}%")
                elif key == "key_personnel_contains":
                    conditions.append("key_personnel LIKE %s")
                    params.append(f"%{value}%")
                elif key == "borrowers_profile_contains":
                    conditions.append("borrowers_profile LIKE %s")
                    params.append(f"%{value}%")
                elif key == "shareholding_profile_contains":
                    conditions.append("shareholding_profile LIKE %s")
                    params.append(f"%{value}%")
                
                # Specific JSON field extractions and comparisons
                elif key.startswith("eps_"):
                    field_path = "$..[?(@.EPS)]"
                    if key == "eps_min":
                        conditions.append("JSON_EXTRACT(key_metrics, %s) >= %s")
                        params.append(field_path, value)
                    elif key == "eps_max":
                        conditions.append("JSON_EXTRACT(key_metrics, %s) <= %s")
                        params.append(field_path, value)
                    elif key == "eps_equals":
                        conditions.append("JSON_EXTRACT(key_metrics, %s) = %s")
                        params.append(field_path, value)
                
                elif key.startswith("debt_equity_"):
                    field_path = "$..[?(@.Debt/Equity)]"
                    if key == "debt_equity_min":
                        conditions.append("JSON_EXTRACT(key_metrics, %s) >= %s")
                        params.append(field_path, value)
                    elif key == "debt_equity_max":
                        conditions.append("JSON_EXTRACT(key_metrics, %s) <= %s")
                        params.append(field_path, value)
                    elif key == "debt_equity_equals":
                        conditions.append("JSON_EXTRACT(key_metrics, %s) = %s")
                        params.append(field_path, value)
                
                elif key.startswith("current_ratio_"):
                    field_path = "$..[?(@.Current ratio)]"
                    if key == "current_ratio_min":
                        conditions.append("JSON_EXTRACT(key_metrics, %s) >= %s")
                        params.append(field_path, value)
                    elif key == "current_ratio_max":
                        conditions.append("JSON_EXTRACT(key_metrics, %s) <= %s")
                        params.append(field_path, value)
                    elif key == "current_ratio_equals":
                        conditions.append("JSON_EXTRACT(key_metrics, %s) = %s")
                        params.append(field_path, value)
            
            # Build the SQL query
            sql = f"SELECT {', '.join(sql_columns)} FROM {table}"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += f" LIMIT {limit}"
            
            # Execute the query
            result = execute_query(sql, tuple(params))
            
            # Process JSON fields in the results
            if "results" in result and result["results"]:
                for company in result["results"]:
                    for field in ["key_metrics", "income_statement", "balance_sheet", "cashflow", 
                                 "lenders_profile", "comparison", "borrowers_profile", 
                                 "shareholding_profile", "key_personnel"]:
                        if field in company and isinstance(company[field], str):
                            try:
                                company[field] = json.loads(company[field])
                            except:
                                pass
            
            return result
            
        except Exception as e:
            return {"error": f"Error executing query: {str(e)}"}
