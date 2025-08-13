import os
import requests
import json
import logging

from vanna.chromadb.chromadb_vector import ChromaDB_VectorStore
from vanna.base import VannaBase
from openai import OpenAI

# 获取日志记录器
logger = logging.getLogger(__name__)

class OpenAI_Chat(VannaBase):
    def __init__(self, client=None, config=None):
        VannaBase.__init__(self, config=config)

        # default parameters - can be overrided using config
        self.temperature = 0.7

        if config and "temperature" in config:
            self.temperature = config["temperature"]

        self.top_p = 1

        if config and "top_p" in config:
            self.top_p = config["top_p"]

        # 检查是否使用自定义推理接口
        self.use_custom_inference = False
        if config and "inference_url" in config and config["inference_url"]:
            self.use_custom_inference = True
            self.inference_url = config["inference_url"]
            self.inference_headers = config.get("inference_headers", {})
            logger.info(f"使用自定义推理接口: {self.inference_url}")
            return

        logger.info("使用OpenAI兼容接口")

        if "api_type" in config:
            raise Exception(
                "Passing api_type is now deprecated. Please pass an OpenAI client instead."
            )

        if "api_base" in config:
            raise Exception(
                "Passing api_base is now deprecated. Please pass an OpenAI client instead."
            )

        if "api_version" in config:
            raise Exception(
                "Passing api_version is now deprecated. Please pass an OpenAI client instead."
            )

        if client is not None:
            self.client = client
            logger.info("使用提供的OpenAI客户端")
            return

        if config is None and client is None:
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            logger.info("使用默认OpenAI配置")
            return

        if config and "api_key" in config:
            self.client = OpenAI(api_key=config["api_key"])

        if config and "api_key" in config and "base_url" in config:
            logger.info(f"使用自定义base_url: {config['base_url']}")
            self.client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])

    def system_message(self, message: str) -> any:
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> any:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> any:
        return {"role": "assistant", "content": message}

    def _call_custom_inference_api(self, messages, **kwargs):
        """调用自定义推理API - 适配 /v1/completions 接口"""
        try:
            logger.info(f"调用自定义推理API: {self.inference_url}")
            
            # 将消息转换为单一的 prompt 文本（completions API 使用 prompt 而不是 messages）
            prompt = self._convert_messages_to_prompt(messages)
            
            # 准备请求数据（completions API 格式）
            request_data = {
                "prompt": prompt,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "model": kwargs.get("model", self.config.get("model", "default")),
                "max_tokens": kwargs.get("max_tokens", 2048),
                "stop": kwargs.get("stop", None)
            }
            
            # 发送 POST 请求到 /v1/completions 接口
            response = requests.post(
                self.inference_url,
                json=request_data,
                headers=self.inference_headers,
                timeout=60
            )
            
            logger.info(f"收到响应，状态码: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            # 解析 completions API 的响应格式
            if "choices" in result and len(result["choices"]) > 0:
                # 标准的 completions API 响应格式
                answer = result["choices"][0]["text"].strip()
                logger.info(f"API调用成功，返回答案长度: {len(answer)}")
                return answer
            elif "text" in result:
                # 简化格式
                answer = result["text"]
                logger.info(f"API调用成功，返回答案长度: {len(answer)}")
                return answer
            elif "response" in result:
                # 备选格式
                answer = result["response"]
                logger.info(f"API调用成功，返回答案长度: {len(answer)}")
                return answer
            else:
                # 如果都没有，返回原始结果
                answer = str(result)
                logger.warning(f"未找到标准响应字段，返回原始结果")
                return answer
                    
        except requests.exceptions.ConnectionError as e:
            logger.error(f"连接错误: {str(e)}")
            logger.error(f"目标URL: {self.inference_url}")
            raise e
        except requests.exceptions.Timeout as e:
            logger.error(f"请求超时: {str(e)}")
            raise e
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"响应状态码: {e.response.status_code}")
                logger.error(f"响应内容: {e.response.text}")
            raise e
        except Exception as e:
            logger.error(f"调用自定义推理API失败: {str(e)}")
            raise e

    def _convert_messages_to_prompt(self, messages):
        """将消息列表转换为单一提示文本（用于 completions API）"""
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"Human: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        # 添加 Assistant: 提示符，让模型知道该生成回复了
        prompt = "\n".join(prompt_parts)
        if not prompt.endswith("Assistant:"):
            prompt += "\nAssistant:"
        
        return prompt

    def submit_prompt(self, prompt, **kwargs) -> str:
        if prompt is None:
            logger.error("Prompt为None")
            raise Exception("Prompt is None")

        if len(prompt) == 0:
            logger.error("Prompt为空")
            raise Exception("Prompt is empty")

        logger.info(f"开始处理prompt，使用自定义推理接口: {self.use_custom_inference}")

        # 如果使用自定义推理接口
        if self.use_custom_inference:
            return self._call_custom_inference_api(prompt, **kwargs)

        # 否则使用 OpenAI（原有逻辑）
        # Count the number of tokens in the message log
        # Use 4 as an approximation for the number of characters per token
        num_tokens = 0
        for message in prompt:
            num_tokens += len(message["content"]) / 4

        try:
            if kwargs.get("model", None) is not None:
                model = kwargs.get("model", None)
                logger.info(f"使用指定model: {model}")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=prompt,
                    stop=None,
                    temperature=self.temperature,
                    top_p=self.top_p,
                )
            elif kwargs.get("engine", None) is not None:
                engine = kwargs.get("engine", None)
                logger.info(f"使用指定engine: {engine}")
                response = self.client.chat.completions.create(
                    engine=engine,
                    messages=prompt,
                    stop=None,
                    temperature=self.temperature,
                    top_p=self.top_p,
                )
            elif self.config is not None and "engine" in self.config:
                logger.info(f"使用config中的engine: {self.config['engine']}")
                response = self.client.chat.completions.create(
                    engine=self.config["engine"],
                    messages=prompt,
                    stop=None,
                    temperature=self.temperature,
                    top_p=self.top_p,
                )
            elif self.config is not None and "model" in self.config:
                logger.info(f"使用config中的model: {self.config['model']}")
                response = self.client.chat.completions.create(
                    model=self.config["model"],
                    messages=prompt,
                    stop=None,
                    temperature=self.temperature,
                    top_p=self.top_p,
                )
            else:
                if num_tokens > 3500:
                    model = "gpt-3.5-turbo-16k"
                else:
                    model = "gpt-3.5-turbo"

                logger.info(f"使用默认model: {model}")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=prompt,
                    stop=None,
                    temperature=self.temperature,
                    top_p=self.top_p,
                )
            
            logger.info("OpenAI API调用成功")
        
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {str(e)}")
            logger.error(f"客户端配置: {getattr(self.client, '_base_url', 'N/A')}")
            raise e

        # Find the first response from the chatbot that has text in it (some responses may not have text)
        for choice in response.choices:
            if "text" in choice:
                return choice.text

        # If no response with text is found, return the first response's content (which may be empty)
        content = response.choices[0].message.content
        logger.info(f"OpenAI返回内容长度: {len(content) if content else 0}")
        return content


class LocalContext_OpenAI(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)
