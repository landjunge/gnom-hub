import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="config/.env")
keys = {}
idx = 1
for key, value in os.environ.items():
    if key.startswith('OPENROUTER_KEY_FREE_') or key == 'OPENROUTER_API_KEY' or key == 'OPENROUTER_KEY_NVIDIA_NEUTRON' or key == 'OPENROUTER_MANAGEMENT_KEY':
        keys[f"k_{idx}"] = {
            "id": f"k_{idx}",
            "key": value,
            "provider": "openrouter",
            "valid": True,
            "info": "OK"
        }
        idx += 1

print(f"Uploading {len(keys)} keys...")
r = requests.post("http://127.0.0.1:3002/api/llm/keys", json=keys)
print(r.status_code, r.text)
