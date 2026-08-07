"""本地 OCR：把上传/拍照的图片转成文字，供 DeepSeek 读取。

使用 RapidOCR（onnxruntime 实现），离线、支持中文、轻量。
首次调用会从缓存加载模型（几百 MB，需下载一次）。
"""
import base64
import io
import re
from typing import List

import numpy as np
from PIL import Image

_engine = None


def _get_engine():
    """懒加载 OCR 引擎，避免冷启动拖慢其它请求。"""
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    return _engine


def _data_url_to_image(data_url: str) -> np.ndarray:
    """把 `data:image/...;base64,...` 转成 BGR numpy 数组（OpenCV 格式）。"""
    m = re.match(r"data:image/[^;,]+;base64,(.*)", data_url, re.S)
    if not m:
        raise ValueError("无法识别的图片 dataURL")
    raw = base64.b64decode(m.group(1))
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    return np.asarray(img)[:, :, ::-1]  # RGB -> BGR


def image_to_text(data_url: str) -> str:
    """识别图片中的文字，按行拼接返回；无文字返回空字符串。"""
    arr = _data_url_to_image(data_url)
    result, _ = _get_engine()(arr)
    if not result:
        return ""
    lines: List[str] = []
    for item in result:
        # item 形如 [box, text, score]
        if len(item) >= 2 and item[1]:
            lines.append(str(item[1]).strip())
    return "\n".join(lines)