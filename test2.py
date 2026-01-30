# 1) Imports & Environment Setup
import os
from dotenv import load_dotenv

import openai
import langchain

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_openai import OpenAIEmbeddings, ChatOpenAI

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from langchain_pinecone import PineconeVectorStore


# Load environment variables (.env)
load_dotenv()


# 2) Document Loading (PDFs)
def read_documents(directory_path):
    """
    Load all PDF files from a directory loader pypdf
    """
    loader = PyPDFDirectoryLoader(directory_path)
    documents = loader.load()
    return documents

#raw_documents = read_documents("documents") 

# 3) Document Chunking (Text Splitting)
def split_documents(documents, chunk_size=500, chunk_overlap=50):
    """
    Split documents into smaller overlapping chunks
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(documents)


#documents = split_documents(raw_documents)


# 4) Embedding Model Setup (OpenRouter / OpenAI)
embeddings = OpenAIEmbeddings(api_key ="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",
             base_url="https://openrouter.ai/api/v1",
             model="openai/text-embedding-3-small"
                )



# Embedding dimension check
#vector = embeddings.embed_query("how are you?")
#print("Embedding dimension:", len(vector))  # result: 1536


# 5) Vector Store Initialization (Pinecone)
os.environ["PINECONE_API_KEY"] = "pcsk_36fBD1_BHTiYqAGxexbEbvpGN8H7majYggaxC7ywEm8JNEcBaqsZGrKoKv5dcBh6tSeRB7"

vectorstore = PineconeVectorStore(
    embedding=embeddings,
    index_name="chatbot-bnf"
)


# 6) Language Model (LLM) Setup
llm = ChatOpenAI(
    api_key ="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",
    base_url="https://openrouter.ai/api/v1",
    model="openai/gpt-4o-mini",
    temperature=0
)


# 7) Retrieval Function (Similarity Search)
def retrieve_query(query, k=2):
    """
    Retrieve top-k most similar document chunks from Pinecone
    """
    return vectorstore.similarity_search(query, k=k)


# 8) Prompt Template (System + Human Messages)
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful assistant. Answer in English using ONLY the provided context."
    ),
    (
        "human",
        "Context:\n{context}\n\nQuestion: {question}"
    )
])


# 9) Question Answering Chain (RAG Pipeline)
qa_chain = (
    {
        "context": lambda x: "\n\n".join(
            doc.page_content for doc in x["documents"]
        ),
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
    | StrOutputParser()
)


# 10) End-to-End Question Answering Function
def ask_question(question, k=2):
    """
    Full RAG pipeline:
    Question -> Retrieval -> LLM Answer
    """
    docs = retrieve_query(question, k=k)
    answer = qa_chain.invoke({
        "documents": docs,
        "question": question
    })
    return answer

def get_drug_info(drug_name):
    queries = {
        "indication": f"What is the indication of {drug_name}?",
        "dose": f"What is the pediatric dose of {drug_name}?",
        "max_dose": f"What is the maximum pediatric dose of {drug_name}?"
    }

    results = {}
    combined_text = ""

    for key, query in queries.items():
        answer = ask_question(query)
        results[key] = answer
        combined_text += " " + answer

    results["routes"] = detect_routes_from_text(combined_text)

    return results

# administration route :
import re

def detect_routes_from_text(text):
    """
    Detect available routes of administration from medical text
    """
    routes = set()

    text_lower = text.lower()

    if re.search(r"\boral\b|\bpo\b|by mouth", text_lower):
        routes.add("Oral")

    if re.search(r"\biv\b|\bintravenous\b", text_lower):
        routes.add("IV")

    if re.search(r"\bim\b|\bintramuscular\b", text_lower):
        routes.add("IM")

    return list(routes)

import re

def parse_dose_text(dose_text):
    """
    Extract dose values and type from text.
    Returns: dict {values: [..], unit_type: 'per_day'|'per_dose'}
    """
    text = dose_text.lower()

    # values like 50–75 or 50-75 or single 50
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*mg/kg", text)
    single_match = re.search(r"(\d+(?:\.\d+)?)\s*mg/kg", text)

    values = []
    if range_match:
        values = [float(range_match.group(1)), float(range_match.group(2))]
    elif single_match:
        values = [float(single_match.group(1))]

    # type
    if "mg/kg/day" in text or "per day" in text or "daily" in text:
        unit_type = "per_day"
    elif "mg/kg/dose" in text or "per dose" in text:
        unit_type = "per_dose"
    else:
        unit_type = "unknown"

    return {"values": values, "unit_type": unit_type}


def parse_concentration(conc_text):
    """
    Parse concentration like '250 mg / 5 ml'
    Returns mg_per_ml
    """
    m = re.search(r"(\d+(?:\.\d+)?)\s*mg\s*/\s*(\d+(?:\.\d+)?)\s*ml", conc_text.lower())
    if not m:
        return None
    mg, ml = float(m.group(1)), float(m.group(2))
    return mg / ml


def calculate_dose(weight, dose_value, unit_type, frequency, mg_per_ml):
    """
    Returns dict with mg/day, mg/dose, ml/dose
    """
    if unit_type == "per_day":
        mg_day = weight * dose_value
        mg_dose = mg_day / frequency
    elif unit_type == "per_dose":
        mg_dose = weight * dose_value
        mg_day = mg_dose * frequency
    else:
        return None

    ml_dose = mg_dose / mg_per_ml
    return {
        "mg_day": round(mg_day, 2),
        "mg_dose": round(mg_dose, 2),
        "ml_dose": round(ml_dose, 2),
    }

