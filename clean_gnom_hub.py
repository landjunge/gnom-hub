import os
import glob
import re
base_dir = "/Users/landjunge/workspace/gnom_hub-release"
old_pkg = os.path.join(base_dir, "src", "gnom_hub")
new_pkg = os.path.join(base_dir, "src", "gnom_hub")
if os.path.exists(old_pkg):
    os.rename(old_pkg, new_pkg)
file_map = {
    "hub_app.py": "hub_app.py",
    "hub_mcp.py": "hub_mcp.py",
    "hub_mcp_server.py": "hub_mcp_server.py",
    "hub_mcp_client.py": "hub_mcp_client.py",
    "hub_msg.py": "hub_msg.py",
    "hub_pulse.py": "hub_pulse.py"
}
for old_name, new_name in file_map.items():
    old_path = os.path.join(new_pkg, old_name)
    new_path = os.path.join(new_pkg, new_name)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
text_files = []
for root, dirs, files in os.walk(base_dir):
    if ".git" in root or "__pycache__" in root or "egg-info" in root:
        continue
    for f in files:
        if f.endswith((".py", ".md", ".toml", ".txt")):
            text_files.append(os.path.join(root, f))
replace_map = {
    "hub_app": "hub_app",
    "hub_mcp": "hub_mcp",
    "hub_mcp_server": "hub_mcp_server",
    "hub_mcp_client": "hub_mcp_client",
    "hub_msg": "hub_msg",
    "hub_pulse": "hub_pulse",
    "gnom-hub": "gnom-hub",
    "gnom-hub-mcp": "gnom-hub-mcp",
    "gnom-hub-pulse": "gnom-hub-pulse",
    "gnom-hub-stop": "gnom-hub-stop",
    "gnom_hub.": "gnom_hub.",
    "gnom_hub ": "gnom_hub ",
    "GNOM_HUB_": "GNOM_HUB_",
    "gnom_hub_": "gnom_hub_",
    "Gnom-Hub": "Gnom-Hub",
    "gnom_hub": "gnom_hub"
}
sorted_replaces = sorted(replace_map.items(), key=lambda x: len(x[0]), reverse=True)
for path in text_files:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    new_content = content
    for old_str, new_str in sorted_replaces:
        new_content = new_content.replace(old_str, new_str)
    if new_content != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
print("Cleanup complete.")
