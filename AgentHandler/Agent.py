from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from tools import search_tool, wiki_tool, save_tool, save_to_txt
import time
import random

load_dotenv()

class ResearchResponse(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools: list[str]


def AgentCall():

    try:
        llm = ChatAnthropic(model="claude-3-5-sonnet-20240620")
        print("Using Anthropic Claude model")
    except Exception as e:
        if "overloaded_error" in str(e) or "Overloaded" in str(e):
            print("Anthropic overloaded, switching to OpenAI...")
            llm = ChatOpenAI(model="gpt-4o")
        else:
            raise e
        

    parser = PydanticOutputParser(pydantic_object=ResearchResponse)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are a research assistant that will help VEX teams determine more information about other teams. Only return information about teams competing in the VEX Robotics Competition.
                Answer the user query and use necessary tools. 
                
                IMPORTANT: Return ONLY the JSON object in the specified format. Do not include any explanatory text, introductions, or other content before or after the JSON.
                
                Format your response as:\n{format_instructions}
                """,
            ),
            ("placeholder", "{chat_history}"),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())


    tools = [search_tool, wiki_tool, save_tool]
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )

    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    query = input("What can i help you with? ")

    try:
        raw_response = agent_executor.invoke({"query": query})
    except Exception as e:
        if "overloaded_error" in str(e) or "Overloaded" in str(e):
            print("API overloaded. Waiting 10 seconds before retry...")
            time.sleep(10)
            raw_response = agent_executor.invoke({"query": query})
        else:
            raise e

    try:
        output = raw_response.get("output", "")
        if isinstance(output, list) and len(output) > 0:
            text = output[0].get("text", "")
        elif isinstance(output, str):
            text = output
        else:
            text = str(output)
        
        import json
        import re
        
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
            try:
                json.loads(json_text)
                text = json_text
            except json.JSONDecodeError:
                pass 
        
        structured_response = parser.parse(text)
        print(structured_response)
        
        save_data = f"Topic: {structured_response.topic}\n\nSummary: {structured_response.summary}\n\nSources: {', '.join(structured_response.sources)}\n\nTools Used: {', '.join(structured_response.tools)}"
        save_result = save_to_txt(save_data)
        print(f"\n{save_result}")
        
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(f"Raw response: {raw_response}")
        structured_response = None