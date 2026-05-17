import json
import requests
import backoff
import asyncio
import aiohttp
from typing import Any, List, Dict
import os

class AlibabaModel:
    """阿里云模型适配器 - 支持通义千问等阿里云模型"""
    
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
        
        # 阿里云支持的模型列表
        self.supported_models = {
            "qwen-turbo": "通义千问Turbo版",
            "qwen-plus": "通义千问Plus版", 
            "qwen-max": "通义千问Max版",
            "qwen-7b-chat": "通义千问7B聊天模型",
            "qwen-14b-chat": "通义千问14B聊天模型",
            "baichuan-7b-v1": "百川7B模型",
            "chatglm3-6b": "ChatGLM3-6B模型"
        }
        
        if model_name not in self.supported_models:
            print(f"警告: 模型 {model_name} 可能不是阿里云官方支持的模型")
    
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
            "model": self.model_name,
            "input": input_data,
            "parameters": parameters
        }
        
        return payload
    
    def generate(self, input_string, temperature=0.0):
        """生成文本回复"""
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
    
    async def batch_generate_async(self, messages_list, temperature=0.0):
        """异步批量生成"""
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
        return asyncio.run(self.batch_generate_async(messages_list, temperature))


def create_alibaba_model(api_key, model_name="qwen-plus", max_tokens=2048):
    """创建阿里云模型的便捷函数"""
    return AlibabaModel(
        api_key=api_key,
        model_name=model_name,
        stop_words=[],
        max_new_tokens=max_tokens
    )import json
import requests
import backoff
import asyncio
import aiohttp
from typing import Any, List, Dict
import os

class AlibabaModel:
    """阿里云模型适配器 - 支持通义千问等阿里云模型"""
    
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
        
        # 阿里云支持的模型列表
        self.supported_models = {
            "qwen-turbo": "通义千问Turbo版",
            "qwen-plus": "通义千问Plus版", 
            "qwen-max": "通义千问Max版",
            "qwen-7b-chat": "通义千问7B聊天模型",
            "qwen-14b-chat": "通义千问14B聊天模型",
            "baichuan-7b-v1": "百川7B模型",
            "chatglm3-6b": "ChatGLM3-6B模型"
        }
        
        if model_name not in self.supported_models:
            print(f"警告: 模型 {model_name} 可能不是阿里云官方支持的模型")
    
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
            "model": self.model_name,
            "input": input_data,
            "parameters": parameters
        }
        
        return payload
    
    def generate(self, input_string, temperature=0.0):
        """生成文本回复"""
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
    
    async def batch_generate_async(self, messages_list, temperature=0.0):
        """异步批量生成"""
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
        return asyncio.run(self.batch_generate_async(messages_list, temperature))


def create_alibaba_model(api_key, model_name="qwen-plus", max_tokens=2048):
    """创建阿里云模型的便捷函数"""
    return AlibabaModel(
        api_key=api_key,
        model_name=model_name,
        stop_words=[],
        max_new_tokens=max_tokens
    )