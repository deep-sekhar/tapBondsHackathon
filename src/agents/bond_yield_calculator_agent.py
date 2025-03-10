from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import json
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class BondYieldCalculatorAgent:
    def __init__(self, api_key=None):
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GAI_PS"),
            temperature=0
        )
        
        # Create master prompt
        template = """You are a Bond Yield Calculator Agent that helps users calculate bond yields and prices.

Your task is to calculate either:
1. The price of a bond based on a specified yield (yield-to-price calculation)
2. The yield of a bond based on a specified price (price-to-yield calculation)

You will receive bond data including:
- Bond details (ISIN, issuer name, face value, maturity date)
- Cash flow schedule (payment dates and amounts)
- User's investment parameters (investment date, units, target yield or price)

For yield-to-price calculations:
- Calculate the present value of each future cash flow using the formula: PV = CF / (1 + r)^t
  where CF is the cash flow amount, r is the yield (as decimal), and t is time in years
- Sum these present values to determine the bond price
- Express the price as a percentage of face value and as an absolute amount
- Calculate the total consideration (price × units)

For price-to-yield calculations:
- Use numerical approximation to find the yield that makes the present value of future cash flows equal to the specified price
- Start with a reasonable yield estimate (e.g., coupon rate)
- Iteratively adjust until the calculated price matches the target price
- Express the yield as a percentage

User query: {query}
Bond data: {bond_data}

Provide your calculation with:
1. A clear statement of what you're calculating (price or yield)
2. The bond details used in the calculation
3. The step-by-step calculation for each cash flow
4. The final result with appropriate units
5. Any assumptions made or limitations of the calculation
6. Any missing information that would improve accuracy

If essential information is missing, clearly state what additional data is needed.
"""
        
        self.prompt = PromptTemplate(template=template, input_variables=["query", "bond_data"])
        
        # Update to use newer style (avoid deprecation warning)
        from langchain_core.runnables import RunnableSequence
        self.chain = RunnableSequence(self.prompt, self.llm)
    
    def process_query(self, query, bond_data):
        """Process a bond yield calculator query and return a response."""
        try:
            # Format bond data if it's not already a string
            if not isinstance(bond_data, str):
                bond_data_str = json.dumps(bond_data, indent=2)
            else:
                bond_data_str = bond_data
            
            # Get calculation from LLM
            response = self.chain.invoke({"query": query, "bond_data": bond_data_str})
            
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
                "calculation": content
            }
            
        except Exception as e:
            return {"error": f"Error processing query: {str(e)}"}
