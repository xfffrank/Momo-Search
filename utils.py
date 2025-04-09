from dataclasses import dataclass
import urllib.parse
from json import JSONDecodeError
import requests
from typing import List
import re

import faiss
import numpy as np

from config import IP_ADDRESS, LANGUAGE, TIME_RANGE


@dataclass
class Document:
    title: str = ""
    url: str = ""
    snippet: str = ""
    content: str = ""
    score: float = 0.0

def encode_url(url: str) -> str:
    return urllib.parse.quote(url)


def decode_url(url: str) -> str:
    return urllib.parse.unquote(url)


def escape_special_chars(text):
    # reference: https://core.telegram.org/bots/api#markdownv2-style
    special_chars = r'_\*\[\]\(\)~`>#\+\-=\|\{\}\.\!'
    return re.sub(f'([{special_chars}])', r'\\\1', text)


def escape_special_chars_for_link(text):
    # Inside the (...) part of the inline link and custom emoji definition, 
    # all ')' and '\' must be escaped with a preceding '\' character.
    return re.sub(r'([\\)])', r'\\\1', text)

def convert_to_telegram_markdown(text):
    lines = text.split('\n')
    result = []
    
    for line in lines:
        line = line.strip()

        if '[citation:' in line:
            # Replace [citation:X] with [X]
            line = re.sub(r'\[citation:(\d+)\]', r'[\1]', line)

        # Process headers (### becomes bold)
        if line.startswith('### '):
            header_text = line[4:].strip()
            escaped_text = escape_special_chars(header_text)
            result.append(f"*{escaped_text}*\n")
        
        # Process bullet points
        elif line.strip().startswith('- '):
            bullet_text = line.strip()[2:]
            escaped_text = escape_special_chars(bullet_text)
            result.append(f"• {escaped_text}\n")
        
        # Process horizontal rules (---)
        elif line.strip() == '---':
            result.append("——————————————————————\n")
        
        # Process other lines
        else:
            escaped_text = escape_special_chars(line)
            result.append(f"{escaped_text}\n")
    
    return ''.join(result)


def search(query: str, num_results: int) -> List[Document]:
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
               "Accept-Language": "en-US,en;q=0.5"}
    
    request_str = f"/search?q={encode_url(query)}&time_range={TIME_RANGE}&format=json&language={LANGUAGE}&pageno="
    pageno = 1
    base_url = IP_ADDRESS
    res = []
    while len(res) < num_results:
        url = base_url + request_str + str(pageno)
        response = requests.get(url, headers=headers)

        try:
            response_dict = response.json()
        except JSONDecodeError:
            raise ValueError("JSONDecodeError: Please ensure that the SearXNG instance can return data in JSON format")

        result_dicts = response_dict["results"]
        if not result_dicts:
            break

        for result in result_dicts:
            if "content" in result:
                doc = Document(title=result["title"], url=result["url"], snippet=result["content"])
                res.append(doc)

                if len(res) == num_results:
                    break

        pageno += 1
    
    return res


class FaissRetriever:
    def __init__(self, embedding_model, num_candidates: int = 40, sim_threshold: float = 0.45) -> None:
        self.embedding_model = embedding_model
        self.num_candidates = num_candidates
        self.sim_threshold = sim_threshold
        self.embeddings_dim = embedding_model.get_sentence_embedding_dimension()
        self.reset_state()
    
    def reset_state(self) -> None:
        self.index = faiss.IndexFlatIP(self.embeddings_dim)
        self.documents = []
    
    def encode_doc(self, doc: str | List[str]) -> np.ndarray:
        return self.embedding_model.encode(doc, normalize_embeddings=True)

    def add_documents(self, documents: List[Document]) -> None:
        if not documents:
            print('No documents added to the retriever')
            return
        
        self.reset_state()
        self.documents = documents
        doc_embeddings = self.encode_doc(
            [doc.content if doc.content else doc.snippet for doc in documents])
        self.index.add(doc_embeddings)
    
    def filter_by_sim(self, distances: np.ndarray, indices: np.ndarray) -> np.ndarray:
        cutoff_idx = -1
        for idx, sim in enumerate(distances):
            if sim > self.sim_threshold:
                cutoff_idx = idx
            else:
                break
        top_sim_indices = indices[:cutoff_idx + 1]
        return top_sim_indices

    def get_relevant_documents(self, query: str) -> List[Document]:
        if not self.documents:
            raise ValueError('No documents added to the retriever')
        query_embedding = self.encode_doc(query)
        distances, indices = self.index.search(query_embedding.reshape(1, -1), self.num_candidates)

        # add sim info
        for idx, sim in enumerate(distances[0]):
            self.documents[indices[0][idx]].score = sim

        top_indices = self.filter_by_sim(distances[0], indices[0])
        print(f"Found {len(top_indices)} relevant documents")

        relevant_docs = [self.documents[idx] for idx in top_indices]

        # print titile and sim info
        for idx, doc in enumerate(relevant_docs):
            print(f"{idx+1}. {doc.title} (sim: {doc.score:.2f})")

        return relevant_docs
