# 负责定义关键词抽取的节点

import jieba.analyse
from typing import Tuple, List
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger

# 允许的分词词性，全局常量统一管理
ALLOW_POS: Tuple[str, ...] = (
    "n",    # 名词
    "nr",   # 人名
    "ns",   # 地名
    "nt",   # 机构团体名
    "nz",   # 其他专有名词
    "v",    # 动词
    "vn",   # 名动词
    "a",    # 形容词
    "an",   # 名形词
    "eng",  # 英文
    "i",    # 成语
    "l",    # 常用固定短语
)

async def extract_keywords(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> dict:
    """
    从用户查询中抽取关键词
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: 关键词字典
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "抽取关键字", "status": "running"})

    query = state.get("query", "").strip()
    # 空查询直接返回
    if not query:
        logger.warning("用户查询内容为空，跳过关键词抽取")
        writer({"type": "progress", "step": "抽取关键字", "status": "success"})
        return {"keywords": []}

    # 提取关键词 基于 TF-IDF 算法
    raw_keywords: List[str] = jieba.analyse.extract_tags(query, allowPOS=ALLOW_POS)
    # 合并原句 + 去重
    all_keywords = list(set(raw_keywords + [query]))

    writer({"type": "progress", "step": "抽取关键字", "status": "success"})
    logger.info(f"原始查询: {query}, 抽取关键字: {all_keywords}")

    return {"keywords": all_keywords}