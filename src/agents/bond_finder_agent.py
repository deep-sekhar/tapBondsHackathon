from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class BondFinderAgent:
    def __init__(self, api_key=None):
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GAI_PS", api_key),
            temperature=0
        )
        
        # Create master prompt with limit instructions
        template = """You are a Bond Finder Agent that helps users discover and compare bonds across different platforms. Your goal is to identify the best investment opportunities based on yield, risk, and other factors.

    You analyze bond data from multiple platforms (currently SMEST and FixedIncome) and provide recommendations tailored to the user's needs. You have expertise in comparing yields, credit ratings, maturity dates, and other bond characteristics.

    The bond data provided to you may include:
    - Issuer name: The company or entity that issued the bond
    - ISIN: The unique identifier for the bond
    - Credit rating: The bond's credit rating (e.g., AAA, AA+, A)
    - Yield range: The current yield range of the bond (e.g., 7.5\%-8.0\%)
    - Maturity date: When the bond matures
    - Face value: The face value of the bond
    - Platform availability: Where the bond is available (SMEST, FixedIncome, or both)

    User query: {query}

    Bond data to analyze:
    {bond_data}

    Your task is to:
    1. Analyze the bond data provided
    2. Identify the best investment opportunities based on the user's query
    3. Compare bonds across platforms when applicable
    4. Highlight important factors like yield, credit rating, and maturity
    5. Provide clear recommendations with justifications
    6. ALWAYS limit your recommendations to at most {limit} bonds to avoid overwhelming the user

    When recommending bonds:
    - Prioritize higher yields for similar risk profiles
    - Consider credit ratings as indicators of risk (AAA being lowest risk)
    - Account for maturity dates based on user's time horizon
    - Note platform availability for each recommendation
    - Explain trade-offs between risk and return

    Format your response professionally with clear sections:
    - Summary of findings
    - Top recommendations (with key details for each, maximum of {limit})
    - Comparative analysis (when applicable)
    - Additional considerations

    Remember that you are helping users make important financial decisions, so be thorough, accurate, and balanced in your analysis.
    """
        
        self.prompt = PromptTemplate(template=template, input_variables=["query", "bond_data", "limit"])
        
        # Update to use newer style (avoid deprecation warning)
        from langchain_core.runnables import RunnableSequence
        self.chain = RunnableSequence(self.prompt, self.llm)

    def process_query(self, query, bond_data, limit=4):
        """Process a bond finder query and return recommendations.
        
        Args:
            query (str): User's query about bonds
            bond_data (dict or str): Bond data to analyze
            limit (int): Maximum number of bonds to recommend (default: 5)
        """
        try:
            # Format bond data if it's not already a string
            if not isinstance(bond_data, str):
                bond_data_str = json.dumps(bond_data, indent=2)
            else:
                bond_data_str = bond_data
            
            # Ensure limit is reasonable
            if not limit or limit > 10:
                limit = 4
            
            # Get recommendations from LLM with limit
            response = self.chain.invoke({
                "query": query, 
    "bond_data": bond_data_str,
                "limit": limit})
            
            # Extract content from response
            content = None
            if hasattr(response, "content"):
                content = response.content
            elif isinstance(response, dict) and "text" in response:
                content = response["text"]
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)
            
            return {
                "status": "success",
                "limit_applied": limit,
                "recommendations": content
            }
            
        except Exception as e:
            return {"error": f"Error processing query: {str(e)}"}