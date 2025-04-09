from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils import Document


def expand_docs_by_text_split(docs: List[Document]) -> List[Document]:
    res_docs = []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,  # chunk size (characters)
        chunk_overlap=50,  # chunk overlap (characters)
        add_start_index=True,  # track index in original document
    )
    for doc in docs:
        if len(doc.content) > 100:
            all_splits = text_splitter.split_text(doc.content)
            for split in all_splits:
                res_docs.append(Document(
                    title=doc.title,
                    url=doc.url,
                    snippet=doc.snippet,
                    content=split,
                ))
        else:
            res_docs.append(doc)
    return res_docs


def merge_docs_by_url(docs: List[Document]) -> List[Document]:
    """Merge documents with the same URL by combining their snippets.
    
    Args:
        docs: List of Document objects
        
    Returns:
        List of Document objects with merged snippets for documents with the same URL
    """
    url_to_docs = {}
    
    # Group documents by URL
    for doc in docs:
        if doc.url not in url_to_docs:
            url_to_docs[doc.url] = []
        url_to_docs[doc.url].append(doc)
    
    merged_docs = []
    
    # Merge documents with the same URL
    for doc_list in url_to_docs.values():
        if len(doc_list) == 1:
            # No need to merge if there's only one document with this URL
            merged_docs.append(doc_list[0])
        else:
            # Get the first document as the base
            base_doc = doc_list[0]
            
            # Combine snippets from all documents with the same URL
            combined_content = "\n".join([d.content for d in doc_list])
            
            # Create a new document with the combined snippet
            merged_doc = Document(
                title=base_doc.title,
                url=base_doc.url,
                snippet=base_doc.snippet,
                content=combined_content
            )
            
            merged_docs.append(merged_doc)
    
    return merged_docs
