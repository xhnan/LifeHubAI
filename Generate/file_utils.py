import tempfile
from pathlib import Path
import os
import re


def write_overwrite_atomic(file_path: Path, java_code: str) -> None:
    """推荐：原子写入，先写入同目录临时文件，写入完成后替换目标文件"""
    print(f"开始生成 {file_path}")
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    # 在目标目录创建临时文件，保证同一文件系统以便后续 replace 原子性
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(file_path.parent)) as tmp:
        tmp.write(java_code)
        tmp_name = tmp.name
    # 原子替换（在大多数操作系统上为原子操作）
    Path(tmp_name).replace(file_path)


def write_if_not_exists(file_path: Path, content: str, *, create_parents: bool = True) -> bool:
    """
    如果目标文件不存在则写入并返回 True；若已存在则不覆盖并返回 False。
    实现使用原子独占创建（os.open with O_CREAT|O_EXCL），可避免竞态条件。
    """
    print(f"开始生成 {file_path}")
    file_path = Path(file_path)
    if create_parents:
        file_path.parent.mkdir(parents=True, exist_ok=True)

    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    # 可根据需求加上 os.O_BINARY 在 Windows 上，但通常不需要
    try:
        fd = os.open(str(file_path), flags, 0o644)
    except FileExistsError:
        return False
    except OSError:
        # 其它错误如权限等，重新抛出以便上层处理
        raise
    else:
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
        finally:
            # os.fdopen 关闭时会关闭 fd；这里不需要额外处理
            pass
        return True


def extract_java_code(text: str) -> str:
    match = re.search(r"```java\s*(.*?)```", text, re.S)
    return match.group(1).strip() if match else text.strip()


# 验证文件是否存在
def file_exists(file_path: Path) -> bool:
    return Path(file_path).exists()
