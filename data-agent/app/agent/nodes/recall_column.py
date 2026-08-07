# 负责定义召回字段信息的节点
from typing import Dict, List
import re
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime
from openai import APIStatusError
from app.agent.context import DataAgentContext
from app.agent.llm import get_llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.prompt.prompt_loader import load_prompt

from pydantic import BaseModel, Field
# 定义期望输出结构
class KeywordExpandResp(BaseModel):
    keywords: list[str] = Field(description="召回字段信息后关键词列表")
async def recall_column(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> Dict[str, List[ColumnInfo]]:
    """
    基于关键词+LLM扩写关键词，从向量库召回关联字段
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: 召回字段列表
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回字段", "status": "running"})

    # 安全取值，兼容字段缺失场景
    query = state.get("query", "").strip()
    keywords = state.get("keywords", [])

    embedding_client = runtime.context["embedding_client"]
    column_qdrant_repo = runtime.context["column_qdrant_repository"]

    try:
        # llm = get_llm().with_structured_output(KeywordExpandResp)
        llm = get_llm()
        # 加载提示词并构建链路
        prompt_template = PromptTemplate(
            template=load_prompt("extend_keywords_for_column_recall"),
            input_variables=["query"],
        )
        prompt_input = {"query": query}
        full_prompt = prompt_template.format(**prompt_input)
        log_text = f"""
                          ========== LLM 输入Prompt 召回字段信息=========={prompt_input}
                          ====================================
                          """
        logger.info(log_text)
        str_parser = JsonOutputParser()
        try:
            # LLM 扩展关键词
            ai_msg = await llm.ainvoke(full_prompt)
            # 这里可以正常取 .content
            logger.info(f"recall_column-LLM原始文本响应：{ai_msg.content}")
            # 再执行解析
            extend_result = str_parser.parse(ai_msg.content)

            # 合并关键词并去重
            all_keywords = list(set(keywords + extend_result))
            logger.info(f"字段召回 - 合并后关键词列表: {all_keywords}")
        except OutputParserException as e:
            logger.warning(f"【字段召回失败】模型未返回合法JSON，query={query}, err={str(e)}")
            all_keywords = []
        except Exception as e:
            logger.error(f"【字段召回异常】query={query}", err={str(e)})
            all_keywords = []



        # 向量召回，字典去重
        retrieved_cols_map: Dict[str, ColumnInfo] = {}

        BATCH_SIZE = 4
        # 清除各类空白：空格、全角空格、零宽字符、换行、制表符
        whitespace_pattern = re.compile(r'\s+')
        # 判断是否具备有效语义：至少包含一个中文/英文/数字
        valid_content_pattern = re.compile(r'[\u4e00-\u9fa5a-zA-Z0-9]')

        valid_keywords = []
        for keyword in all_keywords:
            raw = keyword
            # 移除全部空白
            clean = whitespace_pattern.sub('', raw)
            if not clean:
                logger.warning(f"【过滤】全部空白文本 raw={repr(raw)}")
                continue
            # 校验：必须包含至少一个汉字、字母、数字
            if not valid_content_pattern.search(clean):
                logger.warning(f"【过滤】无有效语义，仅标点/符号 raw={repr(raw)}")
                continue
            if len(clean) > 400:
                logger.warning(f"【过滤】文本过长 raw={clean[:100]}...")
                continue
            valid_keywords.append(clean)

        # 分批召回
        for start in range(0, len(valid_keywords), BATCH_SIZE):
            batch_texts = valid_keywords[start: start + BATCH_SIZE]
            try:
                logger.info(f"向量接口，关键词:{batch_texts}")
                vecs = await embedding_client.aembed_documents(batch_texts)
                #当 TEI 异常、实现有 bug 时，返回向量数量！= 请求文本数量 zip（） 静默截断，不会抛异常，导致部分关键词丢失召回
                if len(vecs) != len(batch_texts):
                    logger.warning(f"批量向量化返回向量数量不匹配！输入:{len(batch_texts)},输出:{len(vecs)}")
                # 优先使用enumerate保证索引对齐
                for idx, text in enumerate(batch_texts):
                    vec = vecs[idx]
                    col_list = await column_qdrant_repo.search(vec)
                    logger.info(f"向量数据库 ,文本:{text}，结果：{col_list}")
                    for col in col_list:
                        retrieved_cols_map[col.id] = col

            except APIStatusError as e:
                err_msg = str(e)
                logger.error(f"【批量召回字段异常】batch={batch_texts}, err={err_msg}", exc_info=True)
                # 502 代表TEI宕机，直接终止本轮，不要再循环重试轰炸服务
                if "502" in err_msg:
                    logger.error("TEI服务崩溃(502)，停止本轮所有向量化任务，等待容器重启")
                    break
                # 非502错误，才降级串行重试
                for text in batch_texts:
                    try:
                        vec = await embedding_client.aembed_query(text)
                        col_list = await column_qdrant_repo.search(vec)
                        for col in col_list:
                            retrieved_cols_map[col.id] = col
                    except Exception as ee:
                        logger.error(f"【批量降级串行失败】text={text}, err={str(ee)}")
            except Exception as e:
                logger.error(f"【批量召回未知异常】batch={batch_texts}, err={str(e)}", exc_info=True)

        retrieved_columns = list(retrieved_cols_map.values())
        writer({"type": "progress", "step": "召回字段", "status": "success"})
        logger.info(f"字段召回完成，命中字段ID列表: {list(retrieved_cols_map.keys())}")

        return {"retrieved_columns": retrieved_columns}

    except Exception as exc:
        writer({"type": "progress", "step": "召回字段", "status": "error"})
        logger.error(f"【召回字段信息发生异常】query={query}", err={str(exc)})
        raise