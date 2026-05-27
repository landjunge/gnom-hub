# tbm_pricing.py
MODEL_PRICING = {
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
    "deepseek-chat": {"input": 0.0015, "output": 0.002},
    "stage_3": {"input": 0.002, "output": 0.002},
    "stage_2": {"input": 0.0015, "output": 0.0015},
    "llama3.2": {"input": 0.0005, "output": 0.0005}
}
