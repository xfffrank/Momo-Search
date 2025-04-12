import requests
import os
import random
from typing import List

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

from utils import Document


# temporary patch for crawl4ai  --- start #
# https://github.com/unclecode/crawl4ai/issues/842
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.browser_manager import BrowserManager


async def patched_async_playwright__crawler_strategy_close(self) -> None:
    """
    Close the browser and clean up resources.

    This patch addresses an issue with Playwright instance cleanup where the static instance
    wasn't being properly reset, leading to issues with multiple crawls.

    Issue: https://github.com/unclecode/crawl4ai/issues/842

    Returns:
        None
    """
    await self.browser_manager.close()

    # Reset the static Playwright instance
    BrowserManager._playwright_instance = None


AsyncPlaywrightCrawlerStrategy.close = patched_async_playwright__crawler_strategy_close
# temporary patch for crawl4ai  --- end #


class Crawler:
    def __init__(self):
        self.proxy_list = self.init_proxies()

        self.elements_dict = {
            "https://stock.10jqka.com.cn": "body > div.main-content.clearfix > div.main-fl.fl > div.main-text.atc-content",
            "https://cn.investing.com": [
                "#article", 
                "#__next > div.md\:relative.md\:bg-white > div.relative.flex > div.md\:grid-cols-\[1fr_72px\].md2\:grid-cols-\[1fr_420px\].grid.flex-1.grid-cols-1.px-4.pt-5.font-sans-v2.text-\[\#232526\].antialiased.transition-all.xl\:container.sm\:px-6.md\:gap-6.md\:px-7.md\:pt-10.md2\:gap-8.md2\:px-8.xl\:mx-auto.xl\:gap-10.xl\:px-10 > div.min-w-0 > div.flex.flex-col.gap-6.md\:gap-0 > div.flex.gap-6 > div.flex-1"
            ], 
            "https://finance.sina.com.cn": "#artibody",
            "https://xueqiu.com": "#app > div.container.article__container > article",
        }

        self.config = CrawlerRunConfig(
            target_elements=self._flatten_list(list(self.elements_dict.values())),
            cache_mode=CacheMode.BYPASS,
            stream=True,
        )

    def _flatten_list(self, arr: List[List[str]]) -> List[str]:
        res = []
        def dfs(arr):
            for item in arr:
                if isinstance(item, list):
                    dfs(item)
                else:
                    res.append(item)
        
        dfs(arr)
        return res
    
    def init_proxies(self):
        if os.path.exists('proxy.txt'):
            with open('proxy.txt', 'r') as f:
                return f.read().split('\n')
        else:
            # credit to https://github.com/TheSpeedX/PROXY-List
            url = "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
            response = requests.get(url)
            with open('proxy.txt', 'w') as f:
                f.write(response.text)
            return response.text.split('\n')

    async def crawl_many(self, docs: List[Document]):
        # filter urls by checking if the url contains any of the keys in self.elements_dict
        filtered_docs = [doc for doc in docs if any(key in doc.url for key in self.elements_dict) and doc.score > 0.5]
        print(f"Crawling {len(filtered_docs)} sources")
        if not filtered_docs:
            return

        url_to_doc = {doc.url: doc for doc in filtered_docs}
        urls = list(url_to_doc.keys())
        async with AsyncWebCrawler(
            verbose=True,
            proxy=random.choice(self.proxy_list)  # Rotate proxies
        ) as crawler:
            async for result in await crawler.arun_many(
                urls, 
                config=self.config,
                magic=True,
            ):
                if result.success:
                    print(f"[SUCCESS] {result.url}")
                    url_to_doc[result.url].content = result.markdown.raw_markdown
                else:
                    print(f"[ERROR] {result.url} => {result.error_message}")
