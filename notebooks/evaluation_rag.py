"""
RAG Evaluation Script without Deepeval

This script evaluates the performance of a Retrieval-Augmented Generation (RAG) system
using openai llm and without deepeval library.


Custom modules:
- utility (for RAG-specific operations)
"""

import json
from typing import List, Tuple, Dict, Any
import os
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

def evaluate_rag(retriever,no_of_questions: int = 5):
    """
    Evaluate RAG system using predefined test questions and metrics.

    Args:
        retriever: The retriever component to evaluate
        no_of_questions: Number of test questions to generate
    
    Returns:
        Dict containing evaluation metrics
    """
    #llm=ChatOpenAI(temperature=0, model_name="gpt-4-turbo-preview")
    groq_api_key=os.getenv("GROQ_API_KEY")
    llm=ChatGroq(groq_api_key=groq_api_key,model_name="Llama3-8b-8192")

    # Create evaluation prompt
    eval_prompt = PromptTemplate.from_template("""
    Evaluate the following retrieval results for the question.
    
    Question: {question}
    Retrieved Context: {context}
    
    Rate on a scale of 1-5 (5 being best) for:
    1. Relevance: How relevant is the retrieved information to the question?
    2. Completeness: Does the context contain all necessary information?
    3. Conciseness: Is the retrieved context focused and free of irrelevant information?
    
    Provide ratings in JSON format:
    """)

    #Create evaluation chain
    eval_chain = eval_prompt | llm | StrOutputParser()

    #Generate test questions
    question_gen_prompt = PromptTemplate.from_template(
        """Generate {no_of_questions} diverse test questions about climate change 
        """
    )
    
    question_chain = question_gen_prompt | llm | StrOutputParser()

    questions_text = question_chain.invoke({"no_of_questions":no_of_questions})

    questions=questions_text.split("\n")

    #Evaluate each question
    results=[]
    for question in questions:
        #Get retrieval results
        context = retriever.invoke(question)
        context_text = "\n".join([doc.page_content for doc in context])

        #Evaluate results
        eval_result = eval_chain.invoke({"question":question,"context":context_text})

        results.append(eval_result)

    return {
        "questions":questions,
        "results":results,
    }

