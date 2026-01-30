# 1) Imports & Environment Setup
import os
from dotenv import load_dotenv

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

raw_documents = read_documents("documents") 

# 3) Document Chunking (Text Splitting)
def split_documents(documents, chunk_size=1000, chunk_overlap=100):
    """
    Split documents into smaller overlapping chunks
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(documents)


documents = split_documents(raw_documents)


# 4) Embedding Model Setup (OpenRouter / OpenAI)
embeddings = OpenAIEmbeddings(api_key ="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",
             base_url="https://openrouter.ai/api/v1",
             model="openai/text-embedding-3-small"
                )



# Embedding dimension check
#vector = embeddings.embed_query("how are you?")
#print("Embedding dimension:", len(vector))  # result: 1536


# 5) Vector Store Initialization (Pinecone)
os.environ["PINECONE_API_KEY"] = "pcsk_3r1JVb_LA2hZ5yBWdRt9MChcmc5kzkaVMPXdnho4RYeXq8HsieEY8SSwQvD1nMbeh9BGjV"

vectorstore = PineconeVectorStore.from_documents(
    documents=documents,
    embedding=embeddings,
    index_name="chatbot-medical"
)


# 6) Language Model (LLM) Setup
llm = ChatOpenAI(
    api_key ="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",
    base_url="https://openrouter.ai/api/v1",
    model="openai/gpt-4o-mini",
    temperature=0,
    max_tokens=64
)



# 7) Retrieval Function (Similarity Search)
def retrieve_query(query, k=3):
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












