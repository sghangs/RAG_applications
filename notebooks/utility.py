import os
import sys
from dotenv import load_dotenv
load_dotenv()
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain.vectorstores import FAISS
import textwrap
import pymupdf



def replace_t_with_space(list_of_docs):
    """
    Replaces all tab characters ('\t') with spaces in the page content of each document

    Args:
        list_of_documents: A list of document objects, each with a 'page_content' attribute.

    Returns:
        The modified list of documents with tab characters replaced by spaces.
    """
    for doc in list_of_docs:
        doc.page_content=doc.page_content.replace("\t"," ")
    return list_of_docs

def retrieve_context_per_question(question,retriever):
    """
    Retrieves relevant context and unique URLs for a given question using the chunks query retriever.

    Args:
        question: The question for which to retrieve context and URLs.

    Returns:
        A tuple containing:
        - A string with the concatenated content of relevant documents.
        - A list of unique URLs from the metadata of the relevant documents.
    """
    docs=retriever.invoke(question)
    context=[doc.page_content for doc in docs]
    return context

def show_context(context):
    """
    Display the contents of the provided context list.

    Args:
        context (list): A list of context items to be displayed.

    Prints each context item in the list with a heading indicating its position.
    """
    for i, c in enumerate(context):
        print(f"Context {i + 1}:")
        print(c)
        print("\n")

def encode_pdf(path,chunk_size=1000,chunk_overlap=200):
    """
    Encodes a PDF book into a vector store using HuggingFace embeddings.

    Args:
        path: The path to the PDF file.
        chunk_size: The desired size of each text chunk.
        chunk_overlap: The amount of overlap between consecutive chunks.

    Returns:
        A FAISS vector store containing the encoded book content.
    """
    #Load the Pdf file 
    loader=PyPDFLoader(path)
    docs=loader.load()

    #Split the documents into chunks
    splitter=RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )

    texts=splitter.split_documents(docs)
    cleaned_texts=replace_t_with_space(texts)

    #Embeddings 
    embeddings=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    #Create vector store
    vectorstore=FAISS.from_documents(cleaned_texts,embeddings)

    return vectorstore

def text_wrap(text, width=120):
    """
    Wraps the input text to the specified width.

    Args:
        text (str): The input text to wrap.
        width (int): The width at which to wrap the text.

    Returns:
        str: The wrapped text.
    """
    return textwrap.fill(text, width=width)

def read_pdf_to_string(path):
    """
    Read a PDF document from the specified path and return its content as a string.

    Args:
        path (str): The file path to the PDF document.

    Returns:
        str: The concatenated text content of all pages in the PDF document.

    The function uses the 'fitz' library (PyMuPDF) to open the PDF document, iterate over each page,
    extract the text content from each page, and append it to a single string.
    """
    # Open the PDF document located at the specified path
    doc = pymupdf.open(path)
    content = ""
    # Iterate over each page in the document
    for page_num in range(len(doc)):
        # Get the current page
        page = doc[page_num]
        # Extract the text content from the current page and append it to the content string
        content += page.get_text()
    return content

def encode_from_string(content, chunk_size=1000, chunk_overlap=200):
    """
    Encodes a string into a vector store using OpenAI embeddings.

    Args:
        content (str): The text content to be encoded.
        chunk_size (int): The size of each chunk of text.
        chunk_overlap (int): The overlap between chunks.

    Returns:
        FAISS: A vector store containing the encoded content.

    Raises:
        ValueError: If the input content is not valid.
        RuntimeError: If there is an error during the encoding process.
    """

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Content must be a non-empty string.")

    if not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")

    if not isinstance(chunk_overlap, int) or chunk_overlap < 0:
        raise ValueError("chunk_overlap must be a non-negative integer.")

    try:
        # Split the content into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        chunks = text_splitter.create_documents([content])

        # Assign metadata to each chunk
        for chunk in chunks:
            chunk.metadata['relevance_score'] = 1.0

        # Generate embeddings and create the vector store
        #Embeddings 
        embeddings=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(chunks, embeddings)

    except Exception as e:
        raise RuntimeError(f"An error occurred during the encoding process: {str(e)}")

    return vectorstore



