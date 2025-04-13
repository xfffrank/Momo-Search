# Zen
English | [中文](README_zh.md)

Zen is a LLM-powered daily digest tool. It saves you time by providing insights from the latest news for better decision-making.

## Installation
```bash
pip install -r requirements.txt
```

* Install `SearXNG` and run it locally. I recommend the [docker installation](https://docs.searxng.org/admin/installation-docker.html#installation-docker).
* Set up SearXNG configuration.
```python
SEARCH_NUM_RESULTS = 50
IP_ADDRESS = "http://localhost:8080"
LANGUAGE = ""  # "zh" or "en"
TIME_RANGE = "week"  # "day", "week", "month", "year" or "" for any time
```
* Set up your own LLM API keys and configuration.
    * To get started, you can use the DeepSeek API from [volcengine](https://console.volcengine.com/ark/region:ark+cn-beijing/model/detail?Id=deepseek-r1), which has some free credits.
```python
OPENAI_LIKE_API_KEY = ""
OPENAI_LIKE_BASE_URL = ""
DEEPSEEK_R1 = ""  # model id for deepseek-r1
DEEPSEEK_V3 = ""  # model id for deepseek-v3
```

## Usage
1. Demo. This will trigger a search for the query "NVIDIA stock news today".
```bash
python llm_search.py
```

2. Telegram Bot
> This is for the daily digest notification.

1. Follow this [guide](https://core.telegram.org/bots/features#botfather) to create a bot and get the token. Then type `/start` in the chat with the bot to get the chat id.
Alternatively, you can just ask Claude for instructions (which is what I did).
2. Fill in the `config.py` file with your token and chat id.
```python
TELEGRAM_TOKEN = ""
CHAT_ID = ""
```
3. Run the bot.
```bash
python run_bot.py
```
* By default, the bot will send you a daily digest at 9:00 AM.
You can always change the daily query in `daily_query.txt` and the scheduled time in `config.py`.

## Roadmap
- [x] Perform web search and retrieve relevant sources as LLM context.
- [x] Connect to Telegram bot for query execution and daily digest notification.
- [x] Return messages in Markdown format.
- [x] Refine search keywords with LLM.
- [x] Crawl website content for top N relevant sources.
- [ ] Stream the response from the Agent.
- [ ] Add history chat to the LLM context, with a reset button.
- [ ] Auto change the search time range based on the query.
- [ ] Perhaps add a website filter to get more authoritative sources.
    * For now, I will focus on the financial domain.
- [ ] Create a search plan according to the query.
- [ ] Add "speed" and "deep search" modes to adapt to different queries.
- [ ] Better logging. (Remove "print", save logs to a file.)
- [ ] Add more LLMs support.
