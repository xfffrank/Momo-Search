import asyncio
from os import environ
from typing import List
from datetime import datetime

from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from sentence_transformers import SentenceTransformer

from utils import (search, FaissRetriever, Document, convert_to_telegram_markdown, 
                   escape_special_chars, escape_special_chars_for_link)
from retriever import expand_docs_by_text_split, merge_docs_by_url
from config import OPENAI_LIKE_API_KEY, OPENAI_LIKE_BASE_URL, SEARCH_NUM_RESULTS, model_dict, LANGUAGE
from crawl import Crawler

environ['TOKENIZERS_PARALLELISM'] = "false"


class LLMSearch:
    def __init__(self):
        self.rewriter = Agent(
            model=OpenAILike(
                id=model_dict["query_rewriter"],
                api_key=OPENAI_LIKE_API_KEY,
                base_url=OPENAI_LIKE_BASE_URL,
            )
        )

        self.chat = {
            "speed": self.rewriter,
            "quality": Agent(
                model=OpenAILike(
                    id=model_dict["chat"],
                    api_key=OPENAI_LIKE_API_KEY,
                    base_url=OPENAI_LIKE_BASE_URL,
                )
            )
        }

        self.max_sources = SEARCH_NUM_RESULTS
        self.embedding_model = SentenceTransformer("BAAI/bge-small-zh-v1.5", model_kwargs={"torch_dtype": "float16"})
        self.retriever = FaissRetriever(self.embedding_model)
        self.crawler = Crawler()
    
    def get_today_date(self) -> str:
        return datetime.today().strftime('%Y-%m-%d')
    
    def format_prompt(self, search_results: str, question: str, cur_date: str) -> str:
        search_answer_zh_template = \
        f'''# 以下内容是基于用户发送的消息的搜索结果:
        {search_results}
        在我给你的搜索结果中，每个结果都是[webpage X begin]...[webpage X end]格式的，X代表每篇文章的数字索引。请在适当的情况下在句子末尾引用上下文。请按照引用编号[citation:X]的格式在答案中对应部分引用上下文。如果一句话源自多个上下文，请列出所有相关的引用编号，例如[citation:3][citation:5]，切记不要将引用集中在最后返回引用编号，而是在答案对应部分列出。
        在回答时，请注意以下几点：
        - 今天是{cur_date}。
        - 并非搜索结果的所有内容都与用户的问题密切相关，你需要结合问题，对搜索结果进行甄别、筛选。
        - 对于列举类的问题（如列举所有航班信息），尽量将答案控制在10个要点以内，并告诉用户可以查看搜索来源、获得完整信息。优先提供信息完整、最相关的列举项；如非必要，不要主动告诉用户搜索结果未提供的内容。
        - 对于创作类的问题（如写论文），请务必在正文的段落中引用对应的参考编号，例如[citation:3][citation:5]，不能只在文章末尾引用。你需要解读并概括用户的题目要求，选择合适的格式，充分利用搜索结果并抽取重要信息，生成符合用户要求、极具思想深度、富有创造力与专业性的答案。你的创作篇幅需要尽可能延长，对于每一个要点的论述要推测用户的意图，给出尽可能多角度的回答要点，且务必信息量大、论述详尽。
        - 如果回答很长，请尽量结构化、分段落总结。如果需要分点作答，尽量控制在5个点以内，并合并相关的内容。
        - 对于客观类的问答，如果问题的答案非常简短，可以适当补充一到两句相关信息，以丰富内容。
        - 你需要根据用户要求和回答内容选择合适、美观的回答格式，确保可读性强。
        - 你的回答应该综合多个相关网页来回答，不能重复引用一个网页。
        - 除非用户要求，否则你回答的语言需要和用户提问的语言保持一致。

        # 用户消息为：
        {question}'''
        return search_answer_zh_template
    
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

    def analyze_and_summarize(self, query: str, response: List[Document], mode: str = "speed") -> str:
        formatted_sources = self.format_sources(
            [data.content if data.content else data.snippet for data in response])
        cur_date = self.get_today_date()
        prompt = self.format_prompt(formatted_sources, query, cur_date)
        print(f'Prompt:\n {prompt}')
        
        llm_res = self.chat[mode].run(prompt)
        return self.format_llm_response(llm_res.content, response)
    
    def rewrite_query(self, query: str) -> str:
        # ref: https://github.com/langchain-ai/langchain/blob/master/cookbook/rewrite.ipynb?ref=blog.langchain.dev
        prompt = f"""
        今天是{self.get_today_date()}。
        给定一个问题，请提供一个更适合搜索引擎的查询，查询以'**'结尾。
        在回答时，请注意以下几点：
        - 除改写后的查询外，回答中请勿包含任何其他文本。
        - 除非用户要求，否则你回答的语言需要和用户提问的语言保持一致。

        问题：{query} 回答：
        """
        res = self.rewriter.run(prompt).content
        top_query = res.strip().replace('**', '')
        print(f'Original Query: {query}')
        print(f'Query Rewrite: {top_query}')
        return top_query

    async def process_query(self, user_query: str, query_rewrite: str, mode: str = "speed"):
        """Process a search query and yield intermediate and final results.
        
        Yields:
            int: First yield is the number of relevant documents
            str: Second yield is the final formatted response
        """
        response = search(query_rewrite, self.max_sources)
        self.retriever.add_documents(response)
        relevant_docs = self.retriever.get_relevant_documents(user_query)

        yield len(relevant_docs)

        if mode == "speed":
            final_response = self.analyze_and_summarize(user_query, relevant_docs, mode)
            yield final_response
        elif mode == "quality":
            await self.crawler.crawl_many(relevant_docs)
            docs_w_details = expand_docs_by_text_split(relevant_docs)

            self.retriever.add_documents(docs_w_details)
            relevant_docs_detailed = self.retriever.get_relevant_documents(user_query)
            relevant_docs_final = merge_docs_by_url(relevant_docs_detailed)

            final_response = self.analyze_and_summarize(user_query, relevant_docs_final, mode)
            yield final_response
            

async def demo():
    agent = LLMSearch()
    query = "英伟达今日股价走势" if LANGUAGE == "zh" else "NVIDIA stock news today"
    query_rewrite = agent.rewrite_query(query)
    ans = agent.process_query(query, query_rewrite, mode="speed")
    doc_count = await anext(ans)
    print(f"Found {doc_count} relevant sources")
    final_response = await anext(ans)
    print(final_response)


if __name__ == "__main__":
    asyncio.run(demo())
