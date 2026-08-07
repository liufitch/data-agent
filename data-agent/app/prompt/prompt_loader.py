from pathlib import Path


# 固定 Prompt 根目录，避免多层父级硬编码
PROMPT_ROOT: Path = Path(__file__).parent.parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """
    加载指定名称的 Prompt 文本文件
    :param name: prompt 文件名（不含后缀 .prompt）
    :return: 文件完整文本
    """
    prompt_file = PROMPT_ROOT / f"{name}.prompt"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_file.resolve()}")
    if not prompt_file.is_file():
        raise IsADirectoryError(f"路径不是有效文件: {prompt_file.resolve()}")

    return prompt_file.read_text(encoding="utf-8")