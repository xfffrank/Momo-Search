# Zen
中文 | [English](README.md)

Zen 是一款基于大语言模型（LLM）的每日资讯摘要工具。它通过提供最新新闻的深度分析，帮助您节省时间并做出更明智的决策。

## 安装步骤
```bash
pip install -r requirements.txt
```

* 安装并本地运行 `SearXNG` 搜索引擎。推荐使用 [docker 安装方式](https://docs.searxng.org/admin/installation-docker.html#installation-docker)
* 配置 SearXNG 参数：
```python
SEARCH_NUM_RESULTS = 50          # 搜索结果数量
IP_ADDRESS = "http://localhost:8080"  # 本地服务地址
LANGUAGE = ""       # 搜索语言 "zh" 或 "en"
TIME_RANGE = "week" # 时间范围："day"（天）、"week"（周）、"month"（月）、"year"（年）或 ""（不限）
```
* 配置您的 LLM API 密钥：
    * 可以使用火山引擎的 [DeepSeek API](https://console.volcengine.com/ark/region:ark+cn-beijing/model/detail?Id=deepseek-r1)，新用户可获得免费额度。
```python
OPENAI_LIKE_API_KEY = ""         # API 密钥
OPENAI_LIKE_BASE_URL = ""        # API 基础地址
MODEL_ID = ""                    # 模型ID
```

## 使用指南
1. 运行演示（将自动搜索 "英伟达今日股价走势"）
```bash
python llm_search.py
```

2. Telegram 机器人
> 用于接收每日资讯摘要推送

1. 根据 [官方指南](https://core.telegram.org/bots/features#botfather) 创建机器人并获取 token。在与机器人的聊天窗口中输入 `/start` 获取 chat id（我本人是直接询问 Claude 获得的指引）
2. 在 `config.py` 中配置机器人参数：
```python
TELEGRAM_TOKEN = ""  # 机器人token
CHAT_ID = ""         # 聊天ID
```
3. 启动机器人服务
```bash
python run_bot.py
```
* 默认每天上午9点自动推送摘要，可通过修改 `daily_query.txt` 调整搜索关键词，在 `config.py` 中设置推送时间

## 开发路线图
- [x] 执行网络搜索并获取相关来源作为LLM的上下文。
- [x] 连接Telegram机器人以执行查询和发送每日摘要通知。
- [x] 以Markdown格式返回消息。
- [x] 使用LLM优化搜索关键词。
- [x] 抓取前N个相关来源的网站内容。
- [ ] 从Agent流式传输响应。
- [ ] 根据查询自动调整搜索时间范围。
- [ ] 考虑添加网站过滤器以获取更权威的来源。
    * 目前，我将专注于金融领域。
- [ ] 根据查询创建搜索计划。
- [ ] 添加“快速”和“深度搜索”模式以适应不同的查询需求。
- [ ] 增加日志记录模块，移除print。
- [ ] 支持更多的大语言模型（LLMs）。
