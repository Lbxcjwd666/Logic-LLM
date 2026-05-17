import json
import requests
import backoff
import asyncio
import aiohttp
from typing import Any, List, Dict
import os

class AlibabaModel:
    """阿里云模型适配器"""
    
    def __init__(self, api_key, model_name, stop_words, max_new_tokens, endpoint=None):
        """
        初始化阿里云模型
        
        Args:
            api_key: 阿里云API密钥
            model_name: 模型名称
            stop_words: 停止词列表
            max_new_tokens: 最大生成token数
            endpoint: 自定义端点（可选）
        """
        self.api_key = api_key
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.stop_words = stop_words
        
        # 设置默认端点
        if endpoint:
            self.endpoint = endpoint
        else:
            # 阿里云DashScope API端点
            self.endpoint = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        # 模型映射（阿里云模型名称 -> 标准名称）
        self.model_mapping = {
            "qwen-turbo": "qwen-turbo",
            "qwen-plus": "qwen-plus", 
            "qwen-max": "qwen-max",
            "qwen-7b-chat": "qwen-7b-chat",
            "qwen-14b-chat": "qwen-14b-chat",
            "baichuan-7b-v1": "baichuan-7b-v1",
            "chatglm3-6b": "chatglm3-6b"
        }
    
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def _make_request(self, payload):
        """发送请求到阿里云API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"  # 启用异步
        }
        
        response = requests.post(
            self.endpoint,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"阿里云API请求失败: {response.status_code} - {response.text}")
        
        return response.json()
    
    def _build_payload(self, messages, temperature=0.0, top_p=1.0):
        """构建阿里云API请求负载"""
        # 阿里云API格式
        input_data = {
            "messages": messages
        }
        
        parameters = {
            "result_format": "message",
            "max_tokens": self.max_new_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        if self.stop_words:
            parameters["stop_words"] = self.stop_words
        
        payload = {
            "model": self.model_mapping.get(self.model_name, self.model_name),
            "input": input_data,
            "parameters": parameters
        }
        
        return payload
    
    def chat_generate(self, input_string, temperature=0.0):
        """生成聊天回复"""
        messages = [
            {"role": "user", "content": input_string}
        ]
        
        payload = self._build_payload(messages, temperature)
        response = self._make_request(payload)
        
        # 解析响应
        if "output" in response and "choices" in response["output"]:
            generated_text = response["output"]["choices"][0]["message"]["content"].strip()
            return generated_text
        else:
            raise Exception(f"阿里云API响应格式错误: {response}")
    
    def prompt_generate(self, input_string, temperature=0.0):
        """生成提示回复（兼容旧版API）"""
        # 阿里云主要支持聊天格式，将提示转换为聊天格式
        return self.chat_generate(input_string, temperature)
    
    def generate(self, input_string, temperature=0.0):
        """统一生成接口"""
        return self.chat_generate(input_string, temperature)
    
    async def _async_make_request(self, session, payload):
        """异步发送请求"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }
        
        async with session.post(self.endpoint, headers=headers, json=payload) as response:
            if response.status != 200:
                raise Exception(f"阿里云API异步请求失败: {response.status}")
            return await response.json()
    
    async def batch_chat_generate(self, messages_list, temperature=0.0):
        """批量生成聊天回复"""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for message in messages_list:
                messages = [{"role": "user", "content": message}]
                payload = self._build_payload(messages, temperature)
                tasks.append(self._async_make_request(session, payload))
            
            responses = await asyncio.gather(*tasks)
            
            results = []
            for response in responses:
                if "output" in response and "choices" in response["output"]:
                    generated_text = response["output"]["choices"][0]["message"]["content"].strip()
                    results.append(generated_text)
                else:
                    results.append("")
            
            return results
    
    def batch_generate(self, messages_list, temperature=0.0):
        """批量生成接口"""
        return asyncio.run(self.batch_chat_generate(messages_list, temperature))


# 兼容OpenAI接口的包装器
class AlibabaOpenAIWrapper:
    """阿里云模型包装器，兼容OpenAI接口"""
    
    def __init__(self, api_key, model_name, stop_words, max_new_tokens):
        self.model = AlibabaModel(api_key, model_name, stop_words, max_new_tokens)
    
    def generate(self, input_string, temperature=0.0):
        return self.model.generate(input_string, temperature)
    
    def batch_generate(self, messages_list, temperature=0.0):
        return self.model.batch_generate(messages_list, temperature)import json
import requests
import backoff
import asyncio
import aiohttp
from typing import Any, List, Dict
import os

class AlibabaModel:
    """阿里云模型适配器"""
    
    def __init__(self, api_key, model_name, stop_words, max_new_tokens, endpoint=None):
        """
        初始化阿里云模型
        
        Args:
            api_key: 阿里云API密钥
            model_name: 模型名称
            stop_words: 停止词列表
            max_new_tokens: 最大生成token数
            endpoint: 自定义端点（可选）
        """
        self.api_key = api_key
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.stop_words = stop_words
        
        # 设置默认端点
        if endpoint:
            self.endpoint = endpoint
        else:
            # 阿里云DashScope API端点
            self.endpoint = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        # 模型映射（阿里云模型名称 -> 标准名称）
        self.model_mapping = {
            "qwen-turbo": "qwen-turbo",
            "qwen-plus": "qwen-plus", 
            "qwen-max": "qwen-max",
            "qwen-7b-chat": "qwen-7b-chat",
            "qwen-14b-chat": "qwen-14b-chat",
            "baichuan-7b-v1": "baichuan-7b-v1",
            "chatglm3-6b": "chatglm3-6b"
        }
    
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def _make_request(self, payload):
        """发送请求到阿里云API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"  # 启用异步
        }
        
        response = requests.post(
            self.endpoint,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"阿里云API请求失败: {response.status_code} - {response.text}")
        
        return response.json()
    
    def _build_payload(self, messages, temperature=0.0, top_p=1.0):
        """构建阿里云API请求负载"""
        # 阿里云API格式
        input_data = {
            "messages": messages
        }
        
        parameters = {
            "result_format": "message",
            "max_tokens": self.max_new_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        if self.stop_words:
            parameters["stop_words"] = self.stop_words
        
        payload = {
            "model": self.model_mapping.get(self.model_name, self.model_name),
            "input": input_data,
            "parameters": parameters
        }
        
        return payload
    
    def chat_generate(self, input_string, temperature=0.0):
        """生成聊天回复"""
        messages = [
            {"role": "user", "content": input_string}
        ]
        
        payload = self._build_payload(messages, temperature)
        response = self._make_request(payload)
        
        # 解析响应
        if "output" in response and "choices" in response["output"]:
            generated_text = response["output"]["choices"][0]["message"]["content"].strip()
            return generated_text
        else:
            raise Exception(f"阿里云API响应格式错误: {response}")
    
    def prompt_generate(self, input_string, temperature=0.0):
        """生成提示回复（兼容旧版API）"""
        # 阿里云主要支持聊天格式，将提示转换为聊天格式
        return self.chat_generate(input_string, temperature)
    
    def generate(self, input_string, temperature=0.0):
        """统一生成接口"""
        return self.chat_generate(input_string, temperature)
    
    async def _async_make_request(self, session, payload):
        """异步发送请求"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }
        
        async with session.post(self.endpoint, headers=headers, json=payload) as response:
            if response.status != 200:
                raise Exception(f"阿里云API异步请求失败: {response.status}")
            return await response.json()
    
    async def batch_chat_generate(self, messages_list, temperature=0.0):
        """批量生成聊天回复"""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for message in messages_list:
                messages = [{"role": "user", "content": message}]
                payload = self._build_payload(messages, temperature)
                tasks.append(self._async_make_request(session, payload))
            
            responses = await asyncio.gather(*tasks)
            
            results = []
            for response in responses:
                if "output" in response and "choices" in response["output"]:
                    generated_text = response["output"]["choices"][0]["message"]["content"].strip()
                    results.append(generated_text)
                else:
                    results.append("")
            
            return results
    
    def batch_generate(self, messages_list, temperature=0.0):
        """批量生成接口"""
        return asyncio.run(self.batch_chat_generate(messages_list, temperature))


# 兼容OpenAI接口的包装器
class AlibabaOpenAIWrapper:
    """阿里云模型包装器，兼容OpenAI接口"""
    
    def __init__(self, api_key, model_name, stop_words, max_new_tokens):
        self.model = AlibabaModel(api_key, model_name, stop_words, max_new_tokens)
    
    def generate(self, input_string, temperature=0.0):
        return self.model.generate(input_string, temperature)
    
    def batch_generate(self, messages_list, temperature=0.0):
        return self.model.batch_generate(messages_list, temperature)import json
import requests
import backoff
import asyncio
import aiohttp
from typing import Any, List, Dict
import os

class AlibabaModel:
    """阿里云模型适配器"""
    
    def __init__(self, api_key, model_name, stop_words, max_new_tokens, endpoint=None):
        """
        初始化阿里云模型
        
        Args:
            api_key: 阿里云API密钥
            model_name: 模型名称
            stop_words: 停止词列表
            max_new_tokens: 最大生成token数
            endpoint: 自定义端点（可选）
        """
        self.api_key = api_key
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.stop_words = stop_words
        
        # 设置默认端点
        if endpoint:
            self.endpoint = endpoint
        else:
            # 阿里云DashScope API端点
            self.endpoint = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        # 模型映射（阿里云模型名称 -> 标准名称）
        self.model_mapping = {
            "qwen-turbo": "qwen-turbo",
            "qwen-plus": "qwen-plus", 
            "qwen-max": "qwen-max",
            "qwen-7b-chat": "qwen-7b-chat",
            "qwen-14b-chat": "qwen-14b-chat",
            "baichuan-7b-v1": "baichuan-7b-v1",
            "chatglm3-6b": "chatglm3-6b"
        }
    
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def _make_request(self, payload):
        """发送请求到阿里云API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"  # 启用异步
        }
        
        response = requests.post(
            self.endpoint,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"阿里云API请求失败: {response.status_code} - {response.text}")
        
        return response.json()
    
    def _build_payload(self, messages, temperature=0.0, top_p=1.0):
        """构建阿里云API请求负载"""
        # 阿里云API格式
        input_data = {
            "messages": messages
        }
        
        parameters = {
            "result_format": "message",
            "max_tokens": self.max_new_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        if self.stop_words:
            parameters["stop_words"] = self.stop_words
        
        payload = {
            "model": self.model_mapping.get(self.model_name, self.model_name),
            "input": input_data,
            "parameters": parameters
        }
        
        return payload
    
    def chat_generate(self, input_string, temperature=0.0):
        """生成聊天回复"""
        messages = [
            {"role": "user", "content": input_string}
        ]
        
        payload = self._build_payload(messages, temperature)
        response = self._make_request(payload)
        
        # 解析响应
        if "output" in response and "choices" in response["output"]:
            generated_text = response["output"]["choices"][0]["message"]["content"].strip()
            return generated_text
        else:
            raise Exception(f"阿里云API响应格式错误: {response}")
    
    def prompt_generate(self, input_string, temperature=0.0):
        """生成提示回复（兼容旧版API）"""
        # 阿里云主要支持聊天格式，将提示转换为聊天格式
        return self.chat_generate(input_string, temperature)
    
    def generate(self, input_string, temperature=0.0):
        """统一生成接口"""
        return self.chat_generate(input_string, temperature)
    
    async def _async_make_request(self, session, payload):
        """异步发送请求"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }
        
        async with session.post(self.endpoint, headers=headers, json=payload) as response:
            if response.status != 200:
                raise Exception(f"阿里云API异步请求失败: {response.status}")
            return await response.json()
    
    async def batch_chat_generate(self, messages_list, temperature=0.0):
        """批量生成聊天回复"""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for message in messages_list:
                messages = [{"role": "user", "content": message}]
                payload = self._build_payload(messages, temperature)
                tasks.append(self._async_make_request(session, payload))
            
            responses = await asyncio.gather(*tasks)
            
            results = []
            for response in responses:
                if "output" in response and "choices" in response["output"]:
                    generated_text = response["output"]["choices"][0]["message"]["content"].strip()
                    results.append(generated_text)
                else:
                    results.append("")
            
            return results
    
    def batch_generate(self, messages_list, temperature=0.0):
        """批量生成接口"""
        return asyncio.run(self.batch_chat_generate(messages_list, temperature))


# 兼容OpenAI接口的包装器
class AlibabaOpenAIWrapper:
    """阿里云模型包装器，兼容OpenAI接口"""
    
    def __init__(self, api_key, model_name, stop_words, max_new_tokens):
        self.model = AlibabaModel(api_key, model_name, stop_words, max_new_tokens)
    
    def generate(self, input_string, temperature=0.0):
        return self.model.generate(input_string, temperature)
    
    def batch_generate(self, messages_list, temperature=0.0):
        return self.model.batch_generate(messages_list, temperature)