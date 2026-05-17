"""
阿里云模型配置
"""

# 阿里云模型配置
ALIBABA_MODELS = {
    # 通义千问系列
    "qwen-turbo": {
        "name": "qwen-turbo",
        "description": "通义千问Turbo版，性价比高",
        "max_tokens": 6000,
        "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    },
    "qwen-plus": {
        "name": "qwen-plus", 
        "description": "通义千问Plus版，能力更强",
        "max_tokens": 30000,
        "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    },
    "qwen-max": {
        "name": "qwen-max",
        "description": "通义千问Max版，最强能力",
        "max_tokens": 6000,
        "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    },
    
    # 开源模型系列
    "qwen-7b-chat": {
        "name": "qwen-7b-chat",
        "description": "通义千问7B聊天模型",
        "max_tokens": 8192,
        "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    },
    "qwen-14b-chat": {
        "name": "qwen-14b-chat",
        "description": "通义千问14B聊天模型",
        "max_tokens": 8192,
        "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    },
    
    # 其他模型
    "baichuan-7b-v1": {
        "name": "baichuan-7b-v1",
        "description": "百川7B模型",
        "max_tokens": 4096,
        "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    },
    "chatglm3-6b": {
        "name": "chatglm3-6b",
        "description": "ChatGLM3-6B模型",
        "max_tokens": 8192,
        "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    }
}

# 默认配置
DEFAULT_ALIBABA_MODEL = "qwen-plus"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.0

# 阿里云API配置
def get_alibaba_config():
    """获取阿里云配置"""
    return {
        "api_key": os.getenv('ALIBABA_API_KEY', ''),
        "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "timeout": 60
    }

# 模型能力映射（用于选择合适的模型）
MODEL_CAPABILITIES = {
    "logic_reasoning": ["qwen-max", "qwen-plus", "qwen-14b-chat"],
    "code_generation": ["qwen-plus", "qwen-7b-chat", "baichuan-7b-v1"],
    "creative_writing": ["qwen-max", "qwen-plus"],
    "cost_effective": ["qwen-turbo", "qwen-7b-chat"]
}

def get_recommended_model(use_case="logic_reasoning"):
    """根据使用场景推荐模型"""
    if use_case in MODEL_CAPABILITIES:
        return MODEL_CAPABILITIES[use_case][0]  # 返回第一个推荐模型
    return DEFAULT_ALIBABA_MODEL