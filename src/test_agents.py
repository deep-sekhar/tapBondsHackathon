from agents.bond_directory_agent import BondDirectoryAgent
from agents.bond_screener_agent import BondScreenerAgent
from agents.bond_yield_calculator_agent import BondYieldCalculatorAgent
from agents.bond_finder_agent import BondFinderAgent
import json
from decimal import Decimal
from datetime import date, datetime
from orchestrator import OrchestratorAgent

# Define a custom JSON encoder to handle Decimal and date types
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # Convert Decimal to float for JSON serialization
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()  # Convert dates to ISO format string
        return super(CustomEncoder, self).default(obj)

def test_bond_directory():
    """Test the Bond Directory Agent with various queries."""
    agent = BondDirectoryAgent()
    
    test_queries = [
        # "Show me bonds from BANK OF BARODA",
        # "Show me cash flow dates from BLU-SMART MOBILITY PRIVATE LIMITED",
        "Find bonds with coupon rate higher than 8%",
    ]
    
    for i, query in enumerate(test_queries):
        print(f"\n=== Test {i+1}: {query} ===")
        result = agent.process_query(query)
        
        # Format the output nicely
        if "error" in result:
            print(f"ERROR: {result['error']}")
        else:
            print(f"Found: {result.get('count', 0)} results")
            if result.get("results") and result["results"]:
                # Print first result as sample using the custom encoder
                print(f"Sample result: {json.dumps(result['results'][0], indent=2, cls=CustomEncoder)}")
        print("=" * 50)

def test_bond_screener():
    """Test the Bond Screener Agent with various queries."""
    agent = BondScreenerAgent()
    
    test_queries = [
        "Show me financial metrics for ADITYA BIRLA REAL ESTATE LIMITED",
    ]
    
    for i, query in enumerate(test_queries):
        print(f"\n=== Bond Screener Test {i+1}: {query} ===")
        result = agent.process_query(query)
        
        # Format the output nicely
        if "error" in result:
            print(f"ERROR: {result['error']}")
        else:
            print(f"Found: {result.get('count', 0)} results")
            if result.get("results") and result["results"]:
                # Print first result as sample using the custom encoder
                print(f"Sample result: {json.dumps(result['results'][0], indent=2, cls=CustomEncoder)}")
        print("=" * 50)

def test_bond_finder():
    """Test the Bond Finder Agent with sample bond directory output."""
    agent = BondFinderAgent()
    
    # Sample bond data as if it came from bond directory agent
    sample_bond_data = {
        "results": [
            {
                "isin": "INE123A07X21",
                "company_name": "HDFC Bank Limited",
                "maturity_date": "2026-05-15",
                "coupon_rate": 7.85,
                "credit_rating": "AAA",
                "face_value": 100000,
                "platform": "SMEST",
                "yield_to_maturity": 7.9
            },
            {
                "isin": "INE456B08Y32",
                "company_name": "HDFC Bank Limited",
                "maturity_date": "2028-11-22",
                "coupon_rate": 8.4,
                "credit_rating": "AAA",
                "face_value": 100000,
                "platform": "FixedIncome",
                "yield_to_maturity": 8.3
            },
            {
                "isin": "INE789C09Z43",
                "company_name": "ICICI Bank Limited",
                "maturity_date": "2027-08-10",
                "coupon_rate": 8.1,
                "credit_rating": "AA+",
                "face_value": 100000,
                "platform": "SMEST",
                "yield_to_maturity": 8.2
            },
            {
                "isin": "INE012D10A54",
                "company_name": "ICICI Bank Limited",
                "maturity_date": "2025-03-30",
                "coupon_rate": 7.65,
                "credit_rating": "AA+",
                "face_value": 100000,
                "platform": "FixedIncome",
                "yield_to_maturity": 7.7
            }
        ]
    }
    
    # User query to compare bonds
    query = "Compare bonds from HDFC Bank and ICICI Bank and recommend the best option for a 3-year investment"
    
    # Call the bond finder agent
    result = agent.process_query(query, sample_bond_data, limit=2)
    
    # Print the recommendations
    print("\n=== Bond Comparison Test ===")
    print(f"Query: {query}")
    
    if "error" in result:
        print(f"ERROR: {result['error']}")
    else:
        print(f"\nRecommendations (limit: {result['limit_applied']}):")
        print(result['recommendations'])
    print("=" * 50)

def test_bond_yield_calculator():
    """Test the Bond Yield Calculator Agent with various scenarios including data issues."""
    agent = BondYieldCalculatorAgent()
    
    # Sample bond data with cashflows - including some inconsistencies
    sample_bond_data = {
        "bond_details": {
            "isin": "INE123A07X21",
            "company_name": "ABC Corporation",
            "face_value": 100000,
            "maturity_date": "2026-05-15",  # Future maturity date
            "coupon_rate": 8.5  # Annual coupon rate
        },
        "cashflows": [
            {
                "cash_flow_date": "2023-11-15",  
                "cash_flow_amount": 4250,  
                "principal_amount": 0,
                "interest_amount": 4250
            },
            {
                "cash_flow_date": "2025-05-15",
                "cash_flow_amount": 4250,
                "principal_amount": 0,
                "interest_amount": 4250
            },
            {
                "cash_flow_date": "2025-11-15",
                "cash_flow_amount": 4250,
                "principal_amount": 0,
                "interest_amount": 4250
            },
            {
                "cash_flow_date": "2026-05-15",
                "cash_flow_amount": 104250,  # Final payment with principal
                "principal_amount": 100000,
                "interest_amount": 4250
            }
        ]
    }
    
    # Test queries covering different scenarios
    test_cases = [
        {
            "name": "Price calculation with yield",
            "query": "Calculate the price of this bond today if the yield required is 9.2%",
            "data": sample_bond_data
        },
        {
            "name": "Edge case - incomplete data",
            "query": "Calculate yield to maturity",
            "data": {"bond_details": {"isin": "INE123A07X21", "face_value": 100000}}  # Missing cashflows
        }
    ]
    
    # Run the tests
    for i, test in enumerate(test_cases):
        print(f"\n=== Bond Yield Calculator Test {i+1}: {test['name']} ===")
        print(f"Query: {test['query']}")
        
        result = agent.process_query(test['query'], test['data'])
        
        # Format the output nicely
        if "error" in result:
            print(f"ERROR: {result['error']}")
        else:
            print("Calculation Result:")
            print(result['calculation'])
        print("=" * 50)

def test_orchestrator():
    """Test the Orchestrator with a sample query."""
    orchestrator = OrchestratorAgent()
    
    # Sample query to find bonds from HDFC Bank
    # query = "Show me bonds from BANK OF BARODA"  # Removed the colon
    query = "Show me cashflows from BANK OF BARODA"  # Removed the colon
    # query = "Compare cashflows between ADITYA BIRLA REAL ESTATE LIMITED and BANK OF BARODA"
    
    # Process the query
    try:
        result = orchestrator.process_query(query)
        
        # Print the result
        print("\n=== Orchestrator Test ===")
        print(f"Query: {query}")
        
        if "error" in result:
            print(f"ERROR: {result['error']}")
        else:
            # Use the CustomEncoder to handle date and Decimal objects
            print(f"Response: {json.dumps(result['response'], cls=CustomEncoder, indent=2)}")
    except Exception as e:
        print(f"\n=== Orchestrator Test ===")
        print(f"Query: {query}")
        print(f"ERROR: {str(e)}")
    
    print("=" * 50)

# Add this to the main section
if __name__ == "__main__":
    # print("Testing Bond Directory Agent...")
    # test_bond_directory()
    
    # print("\n\nTesting Bond Screener Agent...")
    # test_bond_screener()

    # print("\n Testing Bond Scanner Agent")
    # test_bond_finder()

    # test_bond_yield_calculator()

    test_orchestrator()
