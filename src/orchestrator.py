import re
from typing import Dict, Any

def classify_query(user_query: str) -> str:
    """
    Classifies the user query into a predefined intent.
    """
    user_query = user_query.lower()
    
    if re.search(r'isin\s+[a-z0-9]+', user_query):
        return "isin_lookup"
    elif re.search(r'find.*bonds|search.*bonds', user_query):
        return "bond_search"
    elif re.search(r'compare.*yield', user_query):
        return "yield_comparison"
    elif re.search(r'(financial|ratio|metrics).*company', user_query):
        return "financial_analysis"
    elif re.search(r'(price|consideration).*bond', user_query):
        return "bond_pricing"
    else:
        return "general_query"

def route_query(intent: str, user_query: str) -> Dict[str, Any]:
    """
    Routes the query to the appropriate agent based on intent.
    """
    if intent == "isin_lookup":
        return isin_lookup_agent(user_query)
    elif intent == "bond_search":
        return bond_search_agent(user_query)
    elif intent == "yield_comparison":
        return yield_comparison_agent(user_query)
    elif intent == "financial_analysis":
        return financial_analysis_agent(user_query)
    elif intent == "bond_pricing":
        return bond_pricing_agent(user_query)
    else:
        return {"response": "I'm not sure how to answer that. Can you clarify?"}

def isin_lookup_agent(query: str) -> Dict[str, Any]:
    return {"response": f"Fetching ISIN details for {query}"}

def bond_search_agent(query: str) -> Dict[str, Any]:
    return {"response": f"Searching for bonds based on {query}"}

def yield_comparison_agent(query: str) -> Dict[str, Any]:
    return {"response": f"Comparing bond yields for {query}"}

def financial_analysis_agent(query: str) -> Dict[str, Any]:
    return {"response": f"Fetching financial analysis for {query}"}

def bond_pricing_agent(query: str) -> Dict[str, Any]:
    return {"response": f"Calculating bond pricing for {query}"}

# Example Usage
if __name__ == "__main__":
    user_query = "Find me secured debentures with a coupon rate above 10% and maturity after 2026."
    intent = classify_query(user_query)
    response = route_query(intent, user_query)
    print(response)
