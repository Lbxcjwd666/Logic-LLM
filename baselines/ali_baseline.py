"""
python ali_baseline.py `
    --api_key "sk-4ccf930e9c494eb1818235daa89a9f32" `
    --model_name "qwen-turbo" `
    --dataset_name "ProntoQA" `
    --split "dev" `
    --mode "Direct" `
    --max_new_tokens 16
"""
import json
import os
from tqdm import tqdm
from collections import OrderedDict
from typing import Dict, List, Tuple
import requests
import argparse

class AlibabaModel:
    '''阿里云模型适配器 - 支持通义千问等阿里云模型'''
    
    def __init__(self, api_key, model_name, stop_words, max_new_tokens):
        self.api_key = api_key
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.stop_words = stop_words if stop_words else ['------']
        # 阿里云DashScope API端点
        self.url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    
    def generate(self, input_string, temperature=0.0):
        '''生成文本回复'''
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        
        # 清理输入字符串，移除可能引起编码问题的字符
        input_string = input_string.encode('utf-8', errors='ignore').decode('utf-8')
        
        # 构建请求负载
        payload = {
            'model': self.model_name,
            'input': {
                'messages': [
                    {'role': 'user', 'content': input_string}
                ]
            },
            'parameters': {
                'temperature': max(0.01, temperature),  # 阿里云API不允许temperature为0
                'max_tokens': self.max_new_tokens,
                'top_p': 0.9
            }
        }
        
        try:
            # 发送请求到阿里云API，设置编码
            response = requests.post(
                self.url, 
                headers=headers, 
                json=payload,
                timeout=60,  # 增加超时时间
            )
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 检查阿里云API响应格式并提取内容
            if 'output' in result:
                if 'choices' in result['output']:
                    # 新版本API格式: {'output': {'choices': [{'message': {'content': ...}}]}}
                    generated_text = result['output']['choices'][0]['message']['content'].strip()
                elif 'text' in result['output']:
                    # 旧版本API格式: {'output': {'text': ...}}
                    generated_text = result['output']['text'].strip()
                else:
                    # 尝试直接使用返回的文本
                    generated_text = str(result['output'])
            else:
                raise Exception(f'阿里云API响应格式错误: {result}')
            
            # 应用停止词逻辑
            for stop_word in self.stop_words:
                if stop_word in generated_text:
                    generated_text = generated_text.split(stop_word)[0].strip()
            
            return generated_text
                
        except requests.exceptions.RequestException as e:
            raise Exception(f'阿里云API请求失败: {str(e)}')
        except UnicodeEncodeError as e:
            raise Exception(f'编码错误: {str(e)}')
    
    def batch_generate(self, messages_list, temperature=0.0):
        '''批量生成文本'''
        results = []
        for message in messages_list:
            try:
                result = self.generate(message, temperature)
                results.append(result)
            except Exception as e:
                print(f'批量生成错误: {e}')
                results.append('')  # 错误时返回空字符串
        return results


class AlibabaBaseline:
    def __init__(self, args):
        self.args = args
        self.data_path = args.data_path
        self.dataset_name = args.dataset_name
        self.split = args.split
        self.model_name = args.model_name
        self.save_path = args.save_path
        self.demonstration_path = args.demonstration_path
        self.mode = args.mode

        # 使用阿里云模型适配器
        self.alibabamodel = AlibabaModel(args.api_key, args.model_name, args.stop_words, args.max_new_tokens)
        
        # 根据模式选择提示词创建函数和标签短语
        if self.mode == 'Direct':
            self.prompt_creator = self.prompt_direct
        elif self.mode == 'CoT':
            self.prompt_creator = self.prompt_cot
        else:
            self.prompt_creator = self.prompt_LSAT  # 默认
        
        self.label_phrase = 'The correct option is:'
    
    def prompt_direct(self, in_context_example, test_example):
        '''Direct模式的提示词 - 强调只输出选项字母'''
        full_prompt = in_context_example
        context = test_example['context'].strip()
        question = test_example['question'].strip()
        options = '\n'.join([opt.strip() for opt in test_example['options']])
        
        full_prompt = full_prompt.replace('[[CONTEXT]]', context)
        full_prompt = full_prompt.replace('[[QUESTION]]', question)
        full_prompt = full_prompt.replace('[[OPTIONS]]', options)
        
        # 在Direct模式下，特别强调只输出选项字母
        full_prompt += "\n\nIMPORTANT: Respond with only the letter of the correct option (A, B, C, or D). Do not provide any reasoning or explanation."
        
        return full_prompt
    
    def prompt_cot(self, in_context_example, test_example):
        '''CoT模式的提示词 - 包含明确的推理和答案分隔符'''
        full_prompt = in_context_example
        context = test_example['context'].strip()
        question = test_example['question'].strip()
        options = '\n'.join([opt.strip() for opt in test_example['options']])
        
        full_prompt = full_prompt.replace('[[CONTEXT]]', context)
        full_prompt = full_prompt.replace('[[QUESTION]]', question)
        full_prompt = full_prompt.replace('[[OPTIONS]]', options)
        
        # 在CoT模式下，添加明确的推理和答案指示
        if '[END]' not in full_prompt:
            # 添加标准的推理到答案的分隔符
            full_prompt += "\n\nLet's think step by step:\n"
        
        return full_prompt

    def prompt_LSAT(self, in_context_example, test_example):
        full_prompt = in_context_example
        context = test_example['context'].strip()
        question = test_example['question'].strip()
        options = '\n'.join([opt.strip() for opt in test_example['options']])
        full_prompt = full_prompt.replace('[[CONTEXT]]', context)
        full_prompt = full_prompt.replace('[[QUESTION]]', question)
        full_prompt = full_prompt.replace('[[OPTIONS]]', options)
        return full_prompt

    def load_in_context_examples(self):
        with open(os.path.join(self.demonstration_path, f'{self.dataset_name}_{self.mode}.txt'), 'r', encoding='utf-8') as f:
            in_context_examples = f.read()
        return in_context_examples

    def load_raw_dataset(self, split):
        with open(os.path.join(self.data_path, self.dataset_name, f'{split}.json'), 'r', encoding='utf-8') as f:
            raw_dataset = json.load(f)
        return raw_dataset

    def reasoning_graph_generation(self):
        # load raw dataset
        raw_dataset = self.load_raw_dataset(self.split)
        print(f"Loaded {len(raw_dataset)} examples from {self.split} split.")

        # load in-context examples
        in_context_examples = self.load_in_context_examples()
        
        outputs = []
        for example in tqdm(raw_dataset):
            question = example['question']

            # create prompt
            full_prompt = self.prompt_creator(in_context_examples, example)
            output = self.alibabamodel.generate(full_prompt)
            
            # get the answer
            label_phrase = self.label_phrase
            generated_answer = output.split(label_phrase)[-1].strip()
            generated_reasoning = output.split(label_phrase)[0].strip()

            # create output
            output = {'id': example['id'], 
                      'question': question, 
                      'answer': example['answer'], 
                      'predicted_reasoning': generated_reasoning,
                      'predicted_answer': generated_answer}
            outputs.append(output)

        # save outputs        
        with open(os.path.join(self.save_path, f'{self.mode}_{self.dataset_name}_{self.split}_{self.model_name}.json'), 'w', encoding='utf-8') as f:
            json.dump(outputs, f, indent=2, ensure_ascii=False)

    def batch_reasoning_graph_generation(self, batch_size=10):
        # load raw dataset
        raw_dataset = self.load_raw_dataset(self.split)
        print(f"Loaded {len(raw_dataset)} examples from {self.split} split.")

        # load in-context examples
        in_context_examples = self.load_in_context_examples()

        outputs = []
        # split dataset into chunks
        dataset_chunks = [raw_dataset[i:i + batch_size] for i in range(0, len(raw_dataset), batch_size)]
        for chunk in tqdm(dataset_chunks):
            # create prompt
            full_prompts = [self.prompt_creator(in_context_examples, example) for example in chunk]
            try:
                batch_outputs = self.alibabamodel.batch_generate(full_prompts)
                # create output
                for sample, output in zip(chunk, batch_outputs):
                    # get the answer
                    dict_output = self.update_answer(sample, output)
                    outputs.append(dict_output)
            except Exception as e:
                print(f'Batch generation failed: {e}')
                # generate one by one if batch generation fails
                for sample, full_prompt in zip(chunk, full_prompts):
                    try:
                        output = self.alibabamodel.generate(full_prompt)
                        # get the answer
                        dict_output = self.update_answer(sample, output)
                        outputs.append(dict_output)
                    except Exception as ex:
                        print(f'Error in generating example {sample["id"]}: {ex}')

        # save outputs        
        with open(os.path.join(self.save_path, f'{self.mode}_{self.dataset_name}_{self.split}_{self.model_name}.json'), 'w', encoding='utf-8') as f:
            json.dump(outputs, f, indent=2, ensure_ascii=False)
    
    def update_answer(self, sample, output):
        label_phrase = self.label_phrase
        
        # 改进的输出解析逻辑
        if self.mode == 'CoT':
            # 对于CoT模式，寻找常见的推理结束标记
            end_markers = ['The correct option is:', 'Therefore, the answer is:', 'So the answer is:', 'Answer:']
            
            generated_reasoning = output
            generated_answer = ''
            
            # 查找第一个匹配的结束标记
            for marker in end_markers:
                if marker in output:
                    parts = output.split(marker)
                    generated_reasoning = parts[0].strip()
                    generated_answer = parts[1].strip() if len(parts) > 1 else ''
                    # 清理答案，只保留选项字母
                    import re
                    answer_match = re.search(r'[A-D]', generated_answer)
                    if answer_match:
                        generated_answer = answer_match.group(0)
                    break
            
            # 如果没有找到标记，尝试按行分割查找答案
            if not generated_answer and '\n' in output:
                lines = output.split('\n')
                # 寻找包含答案的行
                for i, line in enumerate(lines):
                    if any(keyword in line.lower() for keyword in ['answer', 'option', 'therefore', 'thus', 'so', 'hence']):
                        import re
                        answer_match = re.search(r'[A-D]', line)
                        if answer_match:
                            generated_answer = answer_match.group(0)
                            generated_reasoning = '\n'.join(lines[:i]).strip()
                            break
        else:
            # Direct模式保持原有逻辑
            generated_answer = output.split(label_phrase)[-1].strip()
            generated_reasoning = output.split(label_phrase)[0].strip()
        
        dict_output = {'id': sample['id'], 
                        'question': sample['question'], 
                        'answer': sample['answer'], 
                        'predicted_reasoning': generated_reasoning,
                        'predicted_answer': generated_answer}
        return dict_output

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, default='../data')
    parser.add_argument('--dataset_name', type=str)
    parser.add_argument('--split', type=str)
    parser.add_argument('--save_path', type=str, default='./results')
    parser.add_argument('--demonstration_path', type=str, default='./icl_examples')
    parser.add_argument('--api_key', type=str, required=True, help='阿里云API密钥')
    parser.add_argument('--model_name', type=str, default='qwen-plus', help='阿里云模型名称，如qwen-plus, qwen-max等')
    parser.add_argument('--stop_words', type=str, default='------')
    parser.add_argument('--mode', type=str, choices=['Direct', 'CoT'])
    parser.add_argument('--max_new_tokens', type=int, default=2048)
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()
    alibaba_baseline = AlibabaBaseline(args)
    alibaba_baseline.batch_reasoning_graph_generation(batch_size=5)  # 使用较小的批处理大小