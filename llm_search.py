from os import environ
from typing import List
from datetime import datetime

from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from sentence_transformers import SentenceTransformer

from utils import (search, FaissRetriever, Document, convert_to_telegram_markdown, 
                   escape_special_chars, escape_special_chars_for_link)
from config import OPENAI_LIKE_API_KEY, OPENAI_LIKE_BASE_URL, MODEL_ID, SEARCH_NUM_RESULTS


environ['TOKENIZERS_PARALLELISM'] = "false"


class LLMSearch:
    def __init__(self):
        self.agent = Agent(
            model=OpenAILike(
                id=MODEL_ID,
                api_key=OPENAI_LIKE_API_KEY,
                base_url=OPENAI_LIKE_BASE_URL,
            )
        )
        self.max_sources = SEARCH_NUM_RESULTS
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2", model_kwargs={"torch_dtype": "float16"})
        self.retriever = FaissRetriever(self.embedding_model)
    
    def get_today_date(self) -> str:
        return datetime.today().strftime('%Y-%m-%d')
    
    def format_prompt(self, search_results: str, question: str, cur_date: str) -> str:
        search_answer_en_template = \
            f'''# The following contents are the search results related to the user's message:
            {search_results}
            In the search results I provide to you, each result is formatted as [webpage X begin]...[webpage X end], where X represents the numerical index of each article. Please cite the context at the end of the relevant sentence when appropriate. Use the citation format [citation:X] in the corresponding part of your answer. If a sentence is derived from multiple contexts, list all relevant citation numbers, such as [citation:3][citation:5]. Be sure not to cluster all citations at the end; instead, include them in the corresponding parts of the answer.
            When responding, please keep the following points in mind:
            - Today is {cur_date}.
            - Not all content in the search results is closely related to the user's question. You need to evaluate and filter the search results based on the question.
            - For listing-type questions (e.g., listing all flight information), try to limit the answer to 10 key points and inform the user that they can refer to the search sources for complete information. Prioritize providing the most complete and relevant items in the list. Avoid mentioning content not provided in the search results unless necessary.
            - For creative tasks (e.g., writing an essay), ensure that references are cited within the body of the text, such as [citation:3][citation:5], rather than only at the end of the text. You need to interpret and summarize the user's requirements, choose an appropriate format, fully utilize the search results, extract key information, and generate an answer that is insightful, creative, and professional. Extend the length of your response as much as possible, addressing each point in detail and from multiple perspectives, ensuring the content is rich and thorough.
            - If the response is lengthy, structure it well and summarize it in paragraphs. If a point-by-point format is needed, try to limit it to 5 points and merge related content.
            - For objective Q&A, if the answer is very brief, you may add one or two related sentences to enrich the content.
            - Choose an appropriate and visually appealing format for your response based on the user's requirements and the content of the answer, ensuring strong readability.
            - Your answer should synthesize information from multiple relevant webpages and avoid repeatedly citing the same webpage.
            - Unless the user requests otherwise, your response should be in the same language as the user's question.

            # The user's message is:
            {question}'''
        return search_answer_en_template
    
    def format_sources(self, sources: List[str]) -> str:
        sources_str = "\n".join([
            f"[webpage {i+1} begin]{source}[webpage {i+1} end]" for i, source in enumerate(sources)])
        return sources_str
    
    def format_llm_response(self, llm_ans: str, docs: List[Document]) -> str:
        print(f'LLM Answer: \n{llm_ans}')
        llm_ans = convert_to_telegram_markdown(llm_ans)
        print(f'LLM Answer(converted): \n{llm_ans}')

        citations = []
        num_char_limit = 20
        for i, doc in enumerate(docs):
            if len(doc.title) > num_char_limit:
                title = f"{doc.title[:num_char_limit]}..."
            else:
                title = doc.title
            title = escape_special_chars(title)
            url = escape_special_chars_for_link(doc.url)
            citations.append(f"{i+1}\. [{title}]({url})")

        # hide the citation part
        citation_str = '\n'.join([f'>{citation}' for citation in citations]) + '||'
        print(f'Citation: \n{citation_str}')
        return f"{llm_ans}\n\n{citation_str}"

    def analyze_and_summarize(self, query: str, response: List[Document]) -> str:
        formatted_sources = self.format_sources([data.snippet for data in response])
        cur_date = self.get_today_date()
        prompt = self.format_prompt(formatted_sources, query, cur_date)
        print(f'Prompt: {prompt}')
        
        llm_res = self.agent.run(prompt)
        return self.format_llm_response(llm_res.content, response)
    
    def rewrite_query(self, query: str) -> str:
        prompt = f"""
            Today is {self.get_today_date()}.
            Provide a better search query for web search engine to answer the given question, end the queries with '**'. 
            Unless the user requests otherwise, your response should be in the same language as the user's question.
            Question: {query} Answer:
        """
        res = self.agent.run(prompt).content
        top_query = res.split('\n')[0].replace('**', '')
        print(f'Original Query: {query}')
        print(f'Query Rewrite: {top_query}')
        return top_query

    def process_query(self, user_query: str, query_rewrite: str, mode: str = "speed"):
        """Process a search query and yield intermediate and final results.
        
        Yields:
            int: First yield is the number of relevant documents
            str: Second yield is the final formatted response
        """
        response = search(query_rewrite, self.max_sources)
        self.retriever.add_documents(response)
        relevant_docs = self.retriever.get_relevant_documents(user_query)

        yield len(relevant_docs)

        final_response = self.analyze_and_summarize(user_query, relevant_docs)
        yield final_response


if __name__ == "__main__":
    agent = LLMSearch()
    query = "英伟达今日股价走势"
    query_rewrite = agent.rewrite_query(query)
    ans = agent.process_query(query, query_rewrite)
    
    doc_count = next(ans)
    print(f"Found {doc_count} relevant documents")

    final_response = next(ans)
    print(final_response)
