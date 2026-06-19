import requests

agents = requests.get('http://127.0.0.1:3002/api/agents').json()
current_llm = requests.get('http://127.0.0.1:3002/api/llm/agents').json()

config = {}
for a in agents:
    name = a['name'].lower()
    if name in current_llm and current_llm[name]['provider'] == 'openrouter':
        config[name] = current_llm[name]
    else:
        config[name] = {"provider": "openrouter", "model": "deepseek/deepseek-v4-flash:free"}

r = requests.post("http://127.0.0.1:3002/api/llm/agents", json=config)
print(r.status_code, "Updated agents:", list(config.keys()))
