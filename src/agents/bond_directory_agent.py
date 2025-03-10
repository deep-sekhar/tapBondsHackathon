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

class BondDirectoryAgent:
    def __init__(self, api_key=None):
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GAI_PS"),
            temperature=0
        )
        
        # Initialize previous results variable
        self.prev_res = ""
        
        # Create master prompt - NOTE THE DOUBLE BRACES FOR JSON EXAMPLES
        template = """You are a Bond Directory Agent that helps users find information about bonds.
        
        The bond_details table has these columns:
        - isin (string): The unique identifier for a bond
        - company_name (string): The name of the issuing company
        - issue_size (number): The size of the bond issue in crores
        - allotment_date (date): When the bond was allotted
        - maturity_date (date): When the bond matures
        - issuer_details (JSON): Contains issuer_type, sector, industry, etc.
        - instrument_details (JSON): Contains face_value, secured status, instrument description, etc.
        - coupon_details (JSON): Contains coupon_rate, payment frequency, etc.
        - redemption_details (JSON): Contains redemption type, put/call options, etc.
        - credit_rating_details (JSON): Contains ratings from agencies, outlook, etc.
        - listing_details (JSON): Contains exchange listing information, listing date, etc.
        - key_contacts_details (JSON): Contains trustee information, registrar details, etc.
        - key_documents_details (JSON): Contains links to offer documents, rating reports, etc.
        
        The cashflows table has these columns:
        - id (string): Unique identifier for the cash flow record
        - isin (string): The ISIN of the bond this cash flow belongs to
        - cash_flow_date (date): Date when the cash flow occurs
        - cash_flow_amount (decimal): Total amount of the cash flow
        - record_date (date): Record date for the cash flow
        - principal_amount (decimal): Amount of principal being repaid
        - interest_amount (decimal): Amount of interest being paid
        - tds_amount (decimal): Tax deducted at source
        - remaining_principal (decimal): Principal amount remaining after this payment
        - state (string): Status of the cash flow (e.g., "active", "paid")
        - created_at (string): Timestamp when the record was created
        - updated_at (string): Timestamp when the record was last updated
        
        You can filter bonds using these criteria:
        - isin (string): Exact match with ISIN code (=)
        - company_name (string): Partial match with company name (LIKE)
        - maturity_after (date): Bonds maturing after a specific date (format: YYYY-MM-DD) (>)
        - maturity_before (date): Bonds maturing before a specific date (format: YYYY-MM-DD) (<)
        - maturity_equals (date): Bonds maturing on a specific date (format: YYYY-MM-DD) (=)
        - coupon_rate_min (number): Bonds with coupon rate greater than or equal to a value (>=)
        - coupon_rate_max (number): Bonds with coupon rate less than or equal to a value (<=)
        - coupon_rate_equals (number): Bonds with an exact coupon rate (=)
        - secured (string): Whether the bond is secured ("Secured" or "Unsecured") (=)
        - issuer_type (string): Type of issuer (e.g., "PSU", "Non PSU") (=)
        - sector (string): Sector of the issuer (e.g., "Financial Services", "Energy") (=)
        - industry (string): Industry of the issuer (e.g., "Banking", "Power") (=)
        - credit_rating_min (string): Minimum credit rating (e.g., "AA+") (>=)
        - credit_rating_equals (string): Exact credit rating (e.g., "AAA") (=)
        - face_value_min (number): Minimum face value of the bond (>=)
        - face_value_max (number): Maximum face value of the bond (<=)
        - face_value_equals (number): Exact face value of the bond (=)
        - listing_exchange (string): Exchange where bond is listed (e.g., "NSE", "BSE") (=)
        - issue_size_min (number): Minimum issue size in crores (>=)
        - issue_size_max (number): Maximum issue size in crores (<=)
        - issue_size_equals (number): Exact issue size in crores (=)
        
        You can filter cashflows using these criteria:
        - isin (string): Exact match with ISIN code (=)
        - cash_flow_date_after (date): Cash flows occurring after a specific date (format: YYYY-MM-DD) (>)
        - cash_flow_date_before (date): Cash flows occurring before a specific date (format: YYYY-MM-DD) (<)
        - cash_flow_date_equals (date): Cash flows occurring on a specific date (format: YYYY-MM-DD) (=)
        - principal_amount_min (number): Minimum principal amount (>=)
        - principal_amount_max (number): Maximum principal amount (<=)
        - interest_amount_min (number): Minimum interest amount (>=)
        - interest_amount_max (number): Maximum interest amount (<=)
        - state (string): Status of the cash flow (e.g., "active", "paid") (=)
        
        User query: {query}
        {prev_res}
        
        Your task is to:
        1. Determine what information the user is asking for
        2. Identify if this requires data from bond_details, cashflows, or both tables
        3. Construct an optimized SQL query that retrieves ONLY the necessary columns
        4. ALWAYS use LIMIT in your queries to avoid retrieving too much data
        5. Format the query as a JSON object with these fields:
        - table: The table to query (either "bond_details" or "cashflows")
        - columns: Array of column names to retrieve
        - filters: Object with filter conditions
        - limit: Maximum number of results (default 10)
        - compound: Boolean indicating if a follow-up query is needed (e.g., first get bond details, then get cashflows)
        6. If compound is true, also include a "next_query" object with:
        - table: The table to query next
        - columns: Array of column names to retrieve in the second query
        - filters: How to filter the second query (you can reference fields from the first query result)
        - limit: Maximum number of results for the second query ( always under 5 )

        
        Example 1 - Simple bond lookup:
        {{
            "table": "bond_details",
            "columns": ["isin", "company_name"],
            "filters": {{
                "isin": "INE001A07QX9"
            }},
            "limit": 1,
            "compound": true,
            "next_query": {{
                "table": "cashflows",
                "columns": ["cash_flow_date", "cash_flow_amount"],
                "filters": {{
                    "isin": "RESULT_FROM_QUERY_1.isin"
                }},
                "limit": 5
            }}
        }}
        If compound is true, I will use the result from the first query to make a second query.
        
        Example 2 - Cashflow lookup for a bond:
        {{
            "table": "bond_details",
            "columns": ["isin", "company_name"],
            "filters": {{
                "isin": "INE001A07QX9"
            }},
            "limit": 1,
            "compound": true
        }}
        
        Output the JSON query object only, nothing else.
        """
        
        self.prompt = PromptTemplate(template=template, input_variables=["query", "prev_res"])
        
        # Update to use newer style (avoid deprecation warning)
        from langchain_core.runnables import RunnableSequence
        self.chain = RunnableSequence(self.prompt, self.llm)
    
    def process_query(self, query):
        """Process a bond directory query and return a response."""
        try:
            # Add previous results to context if available
            prev_res_context = ""
            if self.prev_res:
                prev_res_context = f"\nResults from previous Query: {self.prev_res}"
            
            # Get query JSON from LLM - updated to new style
            response = self.chain.invoke({"query": query, "prev_res": prev_res_context})
            
            # Debug the response
            print(f"DEBUG - Response type: {type(response)}")
            
            # Extract content from response - handle different response formats
            json_str = None
            if hasattr(response, "content"):
                json_str = response.content
            elif isinstance(response, dict) and "text" in response:
                json_str = response["text"]
            elif isinstance(response, str):
                json_str = response
            else:
                # For AIMessage or other LangChain message types
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
            
            # Reset previous results
            self.prev_res = ""
            
            # Execute the optimized query
            if query_params.get("table") == "bond_details":
                result = self.execute_optimized_query(query_params)
            else:
                result = self.execute_optimized_query2(query_params)


            print("RES: ", result)           
            # Check if compound query is needed
            if query_params.get("compound", False) and "next_query" in query_params:
                # Store the first result
                self.prev_res = json.dumps(result)
                
                # Get the next query parameters from the model's response
                second_query_params = query_params.get("next_query", {})
                
                # Update any filters that reference results from the first query
                for key, value in second_query_params.get("filters", {}).items():
                    if isinstance(value, str) and value.startswith("RESULT_FROM_QUERY_1."):
                        field = value.split(".")[-1]
                        
                        # Extract the field from the nested structure
                        if 'results' in result and isinstance(result['results'], list) and len(result['results']) > 0:
                            if field in result['results'][0]:
                                second_query_params["filters"][key] = result['results'][0][field]
                        elif 'data' in result and isinstance(result['data'], list) and len(result['data']) > 0:
                            if field in result['data'][0]:
                                second_query_params["filters"][key] = result['data'][0][field]
                        elif 'data' in result and isinstance(result['data'], dict) and field in result['data']:
                            second_query_params["filters"][key] = result['data'][field]

                print("Query 2 : ", second_query_params)
                
                # Execute the second query based on its table
                if second_query_params.get("table") == "bond_details":
                    second_result = self.execute_optimized_query(second_query_params)
                else:
                    second_result = self.execute_optimized_query2(second_query_params)

                # Combine results
                combined_result = {
                    "status": "success",
                    "data_part_1": result,
                    "data_part_2": second_result
                }
                
                return combined_result
            
            return result
        except Exception as e:
            return {"error": f"Error processing query: {str(e)}"}
    
    def execute_optimized_query(self, query_params):
        """Execute an optimized TiDB query for bond_details table."""
        try:
            # Extract parameters
            table = "bond_details"  # Ensure we're querying the correct table
            columns = query_params.get("columns", ["isin", "company_name"])
            filters = query_params.get("filters", {})
            limit = query_params.get("limit", 10)
            
            # Ensure limit is applied
            if not limit or limit > 100:
                limit = 5
            
            # Build column list for SQL with comprehensive mappings
            column_mapping = {
                # Coupon details
                "coupon_rate": "JSON_EXTRACT(coupon_details, '$.coupensVo.couponDetails.couponRate') as coupon_rate",
                "coupon_type": "JSON_EXTRACT(coupon_details, '$.coupensVo.couponDetails.couponType') as coupon_type",
                "coupon_frequency": "JSON_EXTRACT(coupon_details, '$.coupensVo.couponDetails.interestPaymentFrequency') as coupon_frequency",
                "coupon_basis": "JSON_EXTRACT(coupon_details, '$.coupensVo.couponDetails.couponBasis') as coupon_basis",
                
                # Instrument details
                "face_value": "JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.faceValue') as face_value",
                "secured": "JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.secured') as secured",
                "instrument_description": "JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.instrumentDesc') as instrument_description",
                "mode_of_issue": "JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.modeOfIssue') as mode_of_issue",
                "tenure_years": "JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.tenureYears') as tenure_years",
                "tenure_months": "JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.tenureMonths') as tenure_months",
                "tenure_days": "JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.tenureDays') as tenure_days",
                "series": "JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.series') as series",
                "tax_free": "JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.taxFree') as tax_free",
                
                # Issuer details
                "issuer_type": "JSON_EXTRACT(issuer_details, '$.issuerTypeOwner') as issuer_type",
                "sector": "JSON_EXTRACT(issuer_details, '$.sector') as sector",
                "industry": "JSON_EXTRACT(issuer_details, '$.industry') as industry",
                "cin": "JSON_EXTRACT(issuer_details, '$.cin') as cin",
                "lei": "JSON_EXTRACT(issuer_details, '$.lei') as lei",
                
                # Credit rating details
                "credit_rating": "JSON_EXTRACT(credit_rating_details, '$.currentRatings.currentRating') as credit_rating",
                "rating_outlook": "JSON_EXTRACT(credit_rating_details, '$.currentRatings.outlook') as rating_outlook",
                "rating_agency": "JSON_EXTRACT(credit_rating_details, '$.currentRatings.creditRatingAgencyName') as rating_agency",
                "rating_date": "JSON_EXTRACT(credit_rating_details, '$.currentRatings.creditRatingDate') as rating_date",
                
                # Listing details
                "listing_exchange": "JSON_EXTRACT(listing_details, '$.listingDetails.exchangeName') as listing_exchange",
                "listing_date": "JSON_EXTRACT(listing_details, '$.listingDetails.listingDate') as listing_date",
                "listing_status": "JSON_EXTRACT(listing_details, '$.listingStatus') as listing_status",
                
                # Redemption details
                "redemption_type": "JSON_EXTRACT(redemption_details, '$.redemptionType') as redemption_type",
                "put_option": "JSON_EXTRACT(redemption_details, '$.putIndicator') as put_option",
                "call_option": "JSON_EXTRACT(redemption_details, '$.callIndicator') as call_option",
                "maturity_type": "JSON_EXTRACT(redemption_details, '$.maturityType') as maturity_type",
                
                # Trustee details
                "debenture_trustee": "JSON_EXTRACT(key_contacts_details, '$.debtTrusteeName') as debenture_trustee",
                "registrar": "JSON_EXTRACT(key_contacts_details, '$.registrar') as registrar",
                "registrar_contact": "JSON_EXTRACT(key_contacts_details, '$.regContact') as registrar_contact",
                "trustee_contact": "JSON_EXTRACT(key_contacts_details, '$.debtTrusteeContact') as trustee_contact",
                "trustee_address": "JSON_EXTRACT(key_contacts_details, '$.debtTrusteeAddr') as trustee_address"
            }
            
            sql_columns = []
            for col in columns:
                if col in column_mapping:
                    sql_columns.append(column_mapping[col])
                else:
                    sql_columns.append(col)
            
            # Build WHERE clause
            conditions = []
            params = []
            
            for key, value in filters.items():
                # ISIN and company name filters
                if key == "isin":
                    if isinstance(value, list):
                        placeholders = ', '.join(['%s'] * len(value))
                        conditions.append(f"isin IN ({placeholders})")
                        params.extend(value)
                    else:
                        conditions.append("isin = %s")
                        params.append(value)
                
                # Maturity date filters
                elif key == "maturity_after":
                    conditions.append("maturity_date >= %s")
                    params.append(value)
                elif key == "maturity_before":
                    conditions.append("maturity_date <= %s")
                    params.append(value)
                elif key == "maturity_equals":
                    conditions.append("maturity_date = %s")
                    params.append(value)
                
                # Coupon rate filters
                elif key == "coupon_rate_min":
                    conditions.append("JSON_EXTRACT(coupon_details, '$.coupensVo.couponDetails.couponRate') >= %s")
                    params.append(value)
                elif key == "coupon_rate_max":
                    conditions.append("JSON_EXTRACT(coupon_details, '$.coupensVo.couponDetails.couponRate') <= %s")
                    params.append(value)
                elif key == "coupon_rate_equals":
                    conditions.append("JSON_EXTRACT(coupon_details, '$.coupensVo.couponDetails.couponRate') = %s")
                    params.append(value)
                
                # Secured status filter
                elif key == "secured":
                    conditions.append("JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.secured') = %s")
                    params.append(value)
                
                # Issuer type, sector, industry filters
                elif key == "issuer_type":
                    conditions.append("JSON_EXTRACT(issuer_details, '$.issuerTypeOwner') = %s")
                    params.append(value)
                elif key == "sector":
                    conditions.append("JSON_EXTRACT(issuer_details, '$.sector') = %s")
                    params.append(value)
                elif key == "industry":
                    conditions.append("JSON_EXTRACT(issuer_details, '$.industry') = %s")
                    params.append(value)

                # Credit rating filters
                elif key == "credit_rating_min":
                    conditions.append("JSON_EXTRACT(credit_rating_details, '$.currentRatings.currentRating') >= %s")
                    params.append(value)
                elif key == "credit_rating_equals":
                    conditions.append("JSON_EXTRACT(credit_rating_details, '$.currentRatings.currentRating') = %s")
                    params.append(value)
                
                # Face value filters
                elif key == "face_value_min":
                    conditions.append("JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.faceValue') >= %s")
                    params.append(value)
                elif key == "face_value_max":
                    conditions.append("JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.faceValue') <= %s")
                    params.append(value)
                elif key == "face_value_equals":
                    conditions.append("JSON_EXTRACT(instrument_details, '$.instrumentsVo.instruments.faceValue') = %s")
                    params.append(value)
                
                # Listing exchange filter
                elif key == "listing_exchange":
                    conditions.append("JSON_EXTRACT(listing_details, '$.listingDetails.exchangeName') = %s")
                    params.append(value)
                
                # Issue size filters
                elif key == "issue_size_min":
                    conditions.append("issue_size >= %s")
                    params.append(value)
                elif key == "issue_size_max":
                    conditions.append("issue_size <= %s")
                    params.append(value)
                elif key == "issue_size_equals":
                    conditions.append("issue_size = %s")
                    params.append(value)
            
            # Build the SQL query
            sql = f"SELECT {', '.join(sql_columns)} FROM tap_bonds.{table}"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += f" LIMIT {limit}"
            
            # Execute the query
            result = execute_query(sql, tuple(params))
            return result
            
        except Exception as e:
            return {"error": f"Error executing query: {str(e)}"}

    def execute_optimized_query2(self, query_params):
        """Execute an optimized TiDB query for cashflows table."""
        try:
            # Extract parameters
            table = "cashflows"  # Ensure we're querying the correct table
            columns = query_params.get("columns", ["id", "isin", "cash_flow_date"])
            filters = query_params.get("filters", {})
            limit = query_params.get("limit", 10)
            
            # Ensure limit is applied
            if not limit or limit > 100:
                limit = 10
            
            # For cashflows table, we don't need JSON extraction
            sql_columns = columns
            
            # Build WHERE clause
            conditions = []
            params = []
            
            for key, value in filters.items():
                # ISIN filter
                if key == "isin":
                    if isinstance(value, list):
                        placeholders = ', '.join(['%s'] * len(value))
                        conditions.append(f"isin IN ({placeholders})")
                        params.extend(value)
                    else:
                        conditions.append("isin = %s")
                        params.append(value)
                
                # Cash flow date filters
                elif key == "cash_flow_date_after":
                    conditions.append("cash_flow_date >= %s")
                    params.append(value)
                elif key == "cash_flow_date_before":
                    conditions.append("cash_flow_date <= %s")
                    params.append(value)
                elif key == "cash_flow_date_equals":
                    conditions.append("cash_flow_date = %s")
                    params.append(value)
                
                # Amount filters
                elif key == "cash_flow_amount_min":
                    conditions.append("cash_flow_amount >= %s")
                    params.append(value)
                elif key == "cash_flow_amount_max":
                    conditions.append("cash_flow_amount <= %s")
                    params.append(value)
                elif key == "cash_flow_amount_equals":
                    conditions.append("cash_flow_amount = %s")
                    params.append(value)
                
                # Principal amount filters
                elif key == "principal_amount_min":
                    conditions.append("principal_amount >= %s")
                    params.append(value)
                elif key == "principal_amount_max":
                    conditions.append("principal_amount <= %s")
                    params.append(value)
                elif key == "principal_amount_equals":
                    conditions.append("principal_amount = %s")
                    params.append(value)
                
                # Interest amount filters
                elif key == "interest_amount_min":
                    conditions.append("interest_amount >= %s")
                    params.append(value)
                elif key == "interest_amount_max":
                    conditions.append("interest_amount <= %s")
                    params.append(value)
                elif key == "interest_amount_equals":
                    conditions.append("interest_amount = %s")
                    params.append(value)
                
                # State filter
                elif key == "state":
                    conditions.append("state = %s")
                    params.append(value)
            
            # Build the SQL query
            sql = f"SELECT {', '.join(sql_columns)} FROM tap_bonds.{table}"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += f" ORDER BY cash_flow_date LIMIT {limit}"

            result = execute_query(sql, params)

            return result
            
        except Exception as e:
            return {"error": f"Error executing query: {str(e)}"}
