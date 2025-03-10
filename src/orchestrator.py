from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import json
import os
from dotenv import load_dotenv
from src.agents.bond_directory_agent import BondDirectoryAgent
from src.agents.bond_screener_agent import BondScreenerAgent
from src.agents.bond_yield_calculator_agent import BondYieldCalculatorAgent
from src.agents.bond_finder_agent import BondFinderAgent

# Load environment variables
load_dotenv()

class OrchestratorAgent:
    def __init__(self, api_key=None):
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GAI_PS", api_key),
            temperature=0.1
        )
        
        # Initialize specialized agents
        self.bond_directory_agent = BondDirectoryAgent()
        self.bond_screener_agent = BondScreenerAgent()
        self.bond_yield_calculator_agent = BondYieldCalculatorAgent()
        self.bond_finder_agent = BondFinderAgent()
        
        # Create master prompt for orchestration
        template = """You are an Orchestrator Agent for the Tap Bonds platform, responsible for routing user queries to specialized agents and compiling their responses.

You have access to four specialized agents:

1. Bond Directory Agent: Provides information on bonds, including ISIN-level details, credit ratings, maturity dates, security types, cash flow schedules, and more.

2. Bond Screener Agent: Performs company-level financial analysis of bond-issuing firms, including financial metrics, ratings, sectors, industries, etc.

3. Bond Yield Calculator Agent: Calculates bond yields and prices. ALWAYS requires data from other agents (typically Bond Directory Agent for cash flows).

4. Bond Finder Agent: Compares bond yields across various platforms. ALWAYS requires data from other agents to provide comprehensive comparisons.

User query: {query}

Your task is to:
1. Analyze the query to determine which agent(s) should handle it
2. Determine the optimal order of agent calls
3. Format your response as a JSON object with these fields:
   - "plan": Array of agent calls in execution order, each with:
     - "agent": Name of the agent to call ("bond_directory", "bond_screener", "bond_yield_calculator", or "bond_finder")
     - "query": The specific query to send to this agent
     - "needs_previous_output": Boolean indicating if this agent needs output from previous agents (ALWAYS true for bond_yield_calculator and bond_finder)
   - "final_compilation_instructions": Instructions on how to compile the final response

Example - Yield calculation requiring data from Bond Directory:
{{
  "plan": [
    {{
      "agent": "bond_directory",
      "query": "Get details and cash flows for ISIN INE567890123",
      "needs_previous_output": false
    }},
    {{
      "agent": "bond_yield_calculator",
      "query": "Calculate yield for ISIN INE567890123 with investment date 2025-03-10 and 10 units at price 102.5",
      "needs_previous_output": true
    }}
  ],
  "final_compilation_instructions": "Present the yield calculation with a clear explanation of the inputs used and the resulting yield percentage."
}}

IMPORTANT: ALWAYS set needs_previous_output to true for Bond Yield Calculator and Bond Finder agents, as they require data from previous agents to function properly.

Output the JSON plan only, nothing else.
"""
        
        self.prompt = PromptTemplate(template=template, input_variables=["query"])
        from langchain_core.runnables import RunnableSequence
        self.chain = RunnableSequence(self.prompt, self.llm)
        
        # Store for accumulated results
        self.agent_results = []
    
    def process_query(self, query):
        """Process a user query through the orchestrator."""
        try:
            # Reset agent results at the start of a new query
            self.agent_results = []
            
            # Get orchestration plan from LLM
            response = self.chain.invoke({"query": query})
            
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
            
            # Clean up the markdown code block formatting
            if json_str.startswith("```"):
                # Extract just the JSON part between the code block markers
                lines = json_str.split("\n")
                # Remove first line (```json) and last line (```
                clean_lines = lines[1:-1] if len(lines) > 2 else lines
                json_str = "\n".join(clean_lines)
            
            # Parse the JSON response
            orchestration_plan = json.loads(json_str)
            
            # Execute the plan
            return self.execute_plan(orchestration_plan, query)
            
        except Exception as e:
            return {"error": f"Error processing query: {str(e)}"}
    
    def execute_plan(self, plan, original_query):
        """Execute the orchestration plan by calling agents in sequence."""
        previous_results = {}
        
        # Execute each agent call in the plan
        for i, agent_call in enumerate(plan["plan"]):
            agent_name = agent_call["agent"]
            agent_query = agent_call["query"]
            needs_previous_output = agent_call["needs_previous_output"]
            
            # Call the appropriate agent
            if agent_name == "bond_directory":
                result = self.bond_directory_agent.process_query(agent_query)
            elif agent_name == "bond_screener":
                result = self.bond_screener_agent.process_query(agent_query)
            elif agent_name == "bond_yield_calculator":
                # Bond Yield Calculator needs previous results
                result = self.bond_yield_calculator_agent.process_query(agent_query, previous_results)
            elif agent_name == "bond_finder":
                # Bond Finder needs previous results
                result = self.bond_finder_agent.process_query(agent_query, previous_results)
            else:
                result = {"error": f"Unknown agent: {agent_name}"}
            
            # Append the result to agent_results (instead of overwriting)
            self.agent_results.append({
                "agent": agent_name,
                "query": agent_query,
                "result": result
            })
            
            # Update previous results for next agent
            previous_results[agent_name] = result
        
        # Compile the final response
        final_response = self._compile_final_response(plan["final_compilation_instructions"], original_query)
        
        return final_response
    
    def _compile_final_response(self, compilation_instructions, original_query):
        """Compile the final response based on all agent results."""
        # Create a prompt for the LLM to compile the results
        compilation_prompt = f"""
        Original user query: {original_query}
        
        Agent results:
        {json.dumps(self.agent_results, indent=2)}
        
        Compilation instructions:
        {compilation_instructions}
        
        Please compile these results into a comprehensive, well-structured response that directly answers the user's query.
        Format your response using Markdown for better readability.
        Include all relevant information from the agent results, but organize it in a coherent way.
        Focus on providing actionable insights and clear explanations.

        MOST IMPORTANT:
        Strictly take care of the decimels and dates in the response and send them as NORMALISED strings so that they can be serialised withtout issues else you get penalty.
        """
        
        # Use the LLM to compile the results
        compilation_response = self.llm.invoke(compilation_prompt)
        
        # Extract content from response
        compiled_text = None
        if hasattr(compilation_response, "content"):
            compiled_text = compilation_response.content
        elif isinstance(compilation_response, dict) and "text" in compilation_response:
            compiled_text = compilation_response["text"]
        elif isinstance(compilation_response, str):
            compiled_text = compilation_response
        else:
            compiled_text = str(compilation_response)
        
        # Return the compiled response
        return {"response": compiled_text}
