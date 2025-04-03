import os
from flask import jsonify
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
load_dotenv()


def chat(request):
    try:
        data = request.json
        query = data.get('query')

        llm =  ChatGroq(
                        temperature=0,
                        groq_api_key=os.getenv("GROQ_API_KEY"),
                        model_name="llama-3.3-70b-versatile"
                )
        prompt = ChatPromptTemplate.from_messages([
                ('system', "Hey, you are an cyber security expert and part of the Botshield project. Botshield is an AI-powered security solution that protects against malicious bots and cyber threats. Answer in 100 words or less"),
                ('human', "{query}"),
            ])

        chain = prompt | llm
        answer = chain.invoke({"query": query})
     
        return jsonify({"answer": answer.content}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500