# -*- coding: utf-8 -*-
"""
client.py —— Hy3（腾讯混元 HY-3）OpenAI 兼容接口封装

仅依赖 Python 标准库（urllib / json），便于在受限环境直接运行。
兼容任意 OpenAI 兼容端点：设置环境变量 API_KEY / BASE_URL / MODEL_NAME。
"""
import os
import json
import urllib.request
import urllib.error
import time


def load_env(path=".env"):
    """极简 .env 解析（不依赖 python-dotenv，保证可移植）。"""
    cfg = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return cfg


class Hy3Client:
    def __init__(self, api_key=None, base_url=None, model=None, env_path=".env", timeout=300):
        env = load_env(env_path)
        self.api_key = api_key or os.getenv("API_KEY") or env.get("API_KEY")
        self.base_url = (base_url or os.getenv("BASE_URL") or env.get("BASE_URL") or "").rstrip("/")
        self.model = model or os.getenv("MODEL_NAME") or env.get("MODEL_NAME") or "hy3"
        self.timeout = timeout
        if not self.api_key or not self.base_url:
            raise RuntimeError(
                "缺少 Hy3 配置：请在 .env 中设置 API_KEY / BASE_URL / MODEL_NAME，"
                "或在构造时传入。config.example.env 可作为模板。"
            )

    def chat(self, system_prompt, user_content, temperature=0.0, max_tokens=2048, retries=4, backoff=2.0):
        """单次对话补全，返回纯文本。带重试与超时。

        说明：Hy3 为推理模型，可能把预算花在 reasoning_content 上而导致最终
        content 为空（HTTP 200 但 message.content==''）。此类情况按「token 受限」
        处理：每次重试将 max_tokens 翻倍，直到拿到非空 content。
        """
        url = f"{self.base_url}/chat/completions"
        last_err = None
        for attempt in range(retries):
            # 逐次翻倍 max_tokens，缓解推理模型把预算耗尽在思考链上
            cur_max = max_tokens * (2 ** attempt)
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": temperature,
                "max_tokens": cur_max,
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                msg = body["choices"][0]["message"]
                content = (msg.get("content") or "")
                # 推理模型偶发 content 为空、内容在 reasoning_content：视为受限，重试
                if content.strip() == "":
                    raise ValueError("empty content (likely token-capped reasoning)")
                return content
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                    KeyError, json.JSONDecodeError, ValueError) as e:
                last_err = e
                if attempt < retries - 1:
                    time.sleep(backoff * (attempt + 1))
        raise RuntimeError(f"Hy3 调用失败（已重试 {retries} 次，max_tokens 增至 {cur_max}）：{last_err}")

    def chat_json(self, system_prompt, user_content, temperature=0.0, max_tokens=2048):
        """要求模型只返回 JSON，并做容错解析（剥离 ```json 代码块 / 前后多余文本）。"""
        text = self.chat(system_prompt, user_content, temperature=temperature, max_tokens=max_tokens)
        return _extract_json(text)


def _extract_json(text):
    """从模型输出中稳健地提取 JSON 对象。"""
    if text is None:
        raise ValueError("模型返回空内容")
    s = text.strip()
    # 去掉可能的 ```json ... ``` 包装
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.lstrip().startswith("json"):
            s = s.lstrip()[4:]
    # 截取首个 { 到末个 }
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start : end + 1]
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"无法解析模型返回的 JSON：{e}\n原始内容：\n{text}")


if __name__ == "__main__":
    c = Hy3Client()
    print(c.chat("你是简洁助手。", "用一句话介绍什么是结构化笔记。", temperature=0.3))
