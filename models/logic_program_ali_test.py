# generate facts and rules based on the problem description

"""
cd d:\KG\Logic-LLM
python models/logic_program_ali_test.py `
    --api_key "sk-4ccf930e9c494eb1818235daa89a9f32" `
    --dataset_name "ProntoQA" `
    --split "dev" `
    --model_name "qwen-max-0428" `
    --max_new_tokens 1024
"""

# generate facts and rules based on the problem description

import json
import os
from tqdm import tqdm
from collections import OrderedDict
from typing import Dict, List, Tuple
import requests
import argparse
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class AlibabaModel:
    '''阿里云模型适配器 - 支持通义千问等阿里云模型'''
    
    def __init__(self, api_key, model_name, stop_words, max_new_tokens):
        self.api_key = api_key
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.stop_words = stop_words if stop_words else ['------']
        # 使用新版API端点
        self.url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        
        # 创建带有重试策略的session
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,  # 总共重试3次
            backoff_factor=1,  # 重试间隔
            status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的状态码
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def generate(self, input_string, temperature=0.0):
        '''生成文本回复'''
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        # 清理输入字符串，移除可能引起编码问题的字符
        input_string = input_string.encode('utf-8', errors='ignore').decode('utf-8')
        
        # 构建请求负载
        payload = {
            'model': self.model_name,
            'messages': [
                {'role': 'user', 'content': input_string}
            ],
            'temperature': max(0.01, temperature),  # 阿里云API不允许temperature为0
            'max_tokens': min(self.max_new_tokens, 1024),  # 降低max_tokens以加快响应
            'top_p': 0.9
        }
        
        max_retries = 5  # 增加重试次数
        for attempt in range(max_retries):
            try:
                # 发送请求到阿里云API，减少超时时间以更快响应
                response = self.session.post(
                    self.url, 
                    headers=headers, 
                    json=payload,
                    timeout=(30, 60),  # 减少读取超时时间
                )
                response.raise_for_status()
                
                # 解析响应
                result = response.json()
                
                # 检查阿里云API响应格式并提取内容
                if 'choices' in result and len(result['choices']) > 0:
                    generated_text = result['choices'][0]['message']['content'].strip()
                else:
                    raise Exception(f'阿里云API响应格式错误: {result}')
                
                # 应用停止词逻辑
                for stop_word in self.stop_words:
                    if stop_word in generated_text:
                        generated_text = generated_text.split(stop_word)[0].strip()
                
                return generated_text
                    
            except requests.exceptions.Timeout as e:
                print(f'第{attempt + 1}次尝试 - 阿里云API请求超时: {str(e)}')
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))  # 递增延迟
                else:
                    print(f'多次尝试后仍然超时，跳过当前请求')
                    return ''
            except requests.exceptions.RequestException as e:
                print(f'第{attempt + 1}次尝试 - 阿里云API请求失败: {str(e)}')
                if 'response' in locals():
                    print(f'错误详情: {response.text}')
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))  # 递增延迟
                else:
                    print(f'多次尝试后仍然失败，跳过当前请求')
                    return ''
            except Exception as e:
                print(f'第{attempt + 1}次尝试 - 未知错误: {str(e)}')
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))  # 递增延迟
                else:
                    print(f'多次尝试后仍然失败，跳过当前请求')
                    return ''
        
        return ''
    
    def batch_generate(self, messages_list, temperature=0.0):
        '''批量生成文本 - 使用循环方式并添加延迟以避免频率限制'''
        results = []
        for i, message in enumerate(messages_list):
            try:
                result = self.generate(message, temperature)
                results.append(result)
                
                # 添加短暂延迟以避免请求频率过高
                if i < len(messages_list) - 1:  # 不是最后一个请求
                    time.sleep(2)  # 延迟2秒
                    
            except Exception as e:
                print(f'批量生成第{i}个错误: {e}')
                results.append('')  # 错误时返回空字符串
        return results


class LogicProgramGenerator:
    def __init__(self, args):
        self.args = args
        self.data_path = args.data_path
        self.dataset_name = args.dataset_name
        self.split = args.split
        self.model_name = args.model_name
        self.save_path = args.save_path

        self.alibabamodel = AlibabaModel(args.api_key, args.model_name, args.stop_words, args.max_new_tokens)
        self.prompt_creator = {'FOLIO': self.prompt_folio,
                               'ProntoQA': self.prompt_prontoqa,
                               'ProofWriter': self.prompt_proofwriter,
                               'LogicalDeduction': self.prompt_logicaldeduction, 
                               'AR-LSAT': self.prompt_arlsat}
        self.load_prompt_templates()
    
    def load_prompt_templates(self):
        prompt_file = f'./models/prompts/{self.dataset_name}.txt'
        if self.dataset_name == 'AR-LSAT' and self.model_name == 'gpt-4':
            prompt_file = f'./models/prompts/{self.dataset_name}-long.txt'
        with open(prompt_file, 'r') as f:
            self.prompt_template = f.read()

    def prompt_folio(self, test_data):
        problem = test_data['context']
        question = test_data['question'].strip()
        full_prompt = self.prompt_template.replace('[[PROBLEM]]', problem).replace('[[QUESTION]]', question)
        return full_prompt

    def prompt_arlsat(self, test_data):
        problem = test_data['context']
        question = test_data['question'].strip()
        choices_str = '\n'.join([f'({choice.strip()}' for choice in test_data['options']]).strip()
        full_prompt = self.prompt_template.replace('[[PROBLEM]]', problem).replace('[[QUESTION]]', question)
        full_prompt = full_prompt.replace('[[CHOICES]]', choices_str)
        return full_prompt
    
    def prompt_prontoqa(self, test_data):
        problem = test_data['context']
        question = test_data['question'].strip()
        full_prompt = self.prompt_template.replace('[[PROBLEM]]', problem).replace('[[QUESTION]]', question)
        return full_prompt
    
    def prompt_proofwriter(self, test_data):
        problem = test_data['context']
        question = test_data['question'].strip()
        full_prompt = self.prompt_template.replace('[[PROBLEM]]', problem).replace('[[QUESTION]]', question)
        return full_prompt
    
    def prompt_logicaldeduction(self, test_data):
        problem = test_data['context']
        question = test_data['question'].strip()
        choices_str = '\n'.join([f'({choice.strip()}' for choice in test_data['options']]).strip()
        full_prompt = self.prompt_template.replace('[[PROBLEM]]', problem).replace('[[QUESTION]]', question)
        full_prompt = full_prompt.replace('[[CHOICES]]', choices_str)
        return full_prompt

    def load_raw_dataset(self, split):
        with open(os.path.join(self.data_path, self.dataset_name, f'{split}.json')) as f:
            raw_dataset = json.load(f)
        return raw_dataset

    def logic_program_generation(self):
        # load raw dataset
        raw_dataset = self.load_raw_dataset(self.split)
        print(f"Loaded {len(raw_dataset)} examples from {self.split} split.")
        
        # 只取前5个数据进行测试
        test_dataset = raw_dataset[:5]
        print(f"Testing with first 5 examples: {[item['id'] for item in test_dataset]}")

        outputs = []
        for example in tqdm(test_dataset, desc="Processing test samples"):
            # create prompt
            try:
                full_prompt = self.prompt_creator[self.dataset_name](example)
                print(f"\n--- Processing example: {example['id']} ---")
                print(f"Prompt:\n{full_prompt}")
                
                output = self.alibabamodel.generate(full_prompt)
                print(f"Generated output:\n{output}")
                print("-" * 50)
                
                programs = [output]

                # create output
                output_dict = {'id': example['id'], 
                        'context': example['context'],
                        'question': example['question'], 
                        'answer': example['answer'],
                        'options': example['options'],
                        'raw_logic_programs': programs}
                outputs.append(output_dict)
            except Exception as e:
                print(f'Error in generating logic programs for example {example["id"]}: {e}')

        # save outputs        
        test_save_path = self.save_path.replace('/logic_programs/', '/logic_programs/test_')
        if not os.path.exists(test_save_path):
            os.makedirs(test_save_path, exist_ok=True)
        
        with open(os.path.join(test_save_path, f'{self.dataset_name}_{self.split}_{self.model_name}_test.json'), 'w') as f:
            json.dump(outputs, f, indent=2, ensure_ascii=False)
        
        print(f"Test results saved to: {os.path.join(test_save_path, f'{self.dataset_name}_{self.split}_{self.model_name}_test.json')}")

    '''
    Updated version of logic_program_generation; speed up the generation process by batching
    '''
    def batch_logic_program_generation(self, batch_size = 1):  # 减少批处理大小到1以确保稳定
        # load raw dataset
        raw_dataset = self.load_raw_dataset(self.split)
        print(f"Loaded {len(raw_dataset)} examples from {self.split} split.")
        
        # 只取前5个数据进行测试
        test_dataset = raw_dataset[:5]
        print(f"Testing with first 5 examples: {[item['id'] for item in test_dataset]}")

        outputs = []
        # split dataset into chunks
        dataset_chunks = [test_dataset[i:i + batch_size] for i in range(0, len(test_dataset), batch_size)]
        for chunk_idx, chunk in enumerate(tqdm(dataset_chunks, desc="Processing test batches")):
            # create prompt
            full_prompts = [self.prompt_creator[self.dataset_name](example) for example in chunk]
            try:
                batch_outputs = self.alibabamodel.batch_generate(full_prompts)
                # create output
                for sample, output in zip(chunk, batch_outputs):
                    print(f"\n--- Processing example: {sample['id']} ---")
                    print(f"Generated output:\n{output}")
                    print("-" * 50)
                    
                    programs = [output]
                    output_dict = {'id': sample['id'], 
                            'context': sample['context'],
                            'question': sample['question'], 
                            'answer': sample['answer'],
                            'options': sample['options'],
                            'raw_logic_programs': programs}
                    outputs.append(output_dict)
            except Exception as e:
                print(f'批处理错误: {e}')
                # generate one by one if batch generation fails
                for sample, full_prompt in zip(chunk, full_prompts):
                    try:
                        print(f"\n--- Processing example: {sample['id']} ---")
                        print(f"Prompt:\n{full_prompt}")
                        
                        output = self.alibabamodel.generate(full_prompt)
                        print(f"Generated output:\n{output}")
                        print("-" * 50)
                        
                        programs = [output]
                        output_dict = {'id': sample['id'], 
                                'context': sample['context'],
                                'question': sample['question'], 
                                'answer': sample['answer'],
                                'options': sample['options'],
                                'raw_logic_programs': programs}
                        outputs.append(output_dict)
                    except Exception as ex:
                        print(f'Error in generating logic programs for example {sample["id"]}: {ex}')

        # remove examples with duplicate ids from the result
        outputs = list({output['id']: output for output in outputs}.values())
        print(f"Generated {len(outputs)} examples.")
        
        # save outputs        
        test_save_path = self.save_path.replace('/logic_programs/', '/logic_programs/test_')
        if not os.path.exists(test_save_path):
            os.makedirs(test_save_path, exist_ok=True)
        
        with open(os.path.join(test_save_path, f'{self.dataset_name}_{self.split}_{self.model_name}_test.json'), 'w') as f:
            json.dump(outputs, f, indent=2, ensure_ascii=False)
        
        print(f"Test results saved to: {os.path.join(test_save_path, f'{self.dataset_name}_{self.split}_{self.model_name}_test.json')}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, default='./data')
    parser.add_argument('--dataset_name', type=str)
    parser.add_argument('--split', type=str, default='dev')
    parser.add_argument('--save_path', type=str, default='./outputs/logic_programs')
    parser.add_argument('--api_key', type=str)
    parser.add_argument('--model_name', type=str, default='qwen-turbo')
    parser.add_argument('--stop_words', type=str, default='------')
    parser.add_argument('--max_new_tokens', type=int, default=1024)
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()
    logic_program_generator = LogicProgramGenerator(args)
    logic_program_generator.batch_logic_program_generation()
