import requests
r = requests.get('https://openrouter.ai/api/v1/models')
models = r.json().get('data', [])
free_models = [m['id'] for m in models if m.get('pricing', {}).get('prompt') == "0" and m.get('pricing', {}).get('completion') == "0"]
print("\n".join(free_models))
