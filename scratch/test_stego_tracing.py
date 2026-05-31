# test_stego_tracing.py — Test steganographic signature embedding in written files
import sys, os, re

# Add project root and src directory to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from gnom_hub.agents.actions.action_write import handle_write
from gnom_hub.soul.zwc_soul import decode_soul

def main():
    print("🧪 Running Steganographic Tracing Test...")
    
    # Workspace directory
    wd = os.path.join(project_root, "gnom_workspace", "default")
    os.makedirs(wd, exist_ok=True)
    
    fname = "test_stego.py"
    fpath = os.path.join(wd, fname)
    if os.path.exists(fpath):
        os.unlink(fpath)
        
    # Simulate a [WRITE] action from CoderAG
    answer = "Hier ist die Datei: [WRITE: test_stego.py]\ndef test_fn():\n    print('Hello World')\n[/WRITE]"
    matches = list(re.finditer(r"\[WRITE:\s*([^\]]+)\](.*?)\[/WRITE\]", answer, re.DOTALL))
    
    agent = {"name": "CoderAG"}
    perms = ["read", "write"]
    
    print("Writing file via handle_write...")
    result = handle_write(answer, matches, agent, perms, bs_mode=False, wd=wd)
    
    # Check if file exists
    if not os.path.exists(fpath):
        print("❌ Error: File test_stego.py was not created.")
        sys.exit(1)
        
    print("File successfully created. Reading file content...")
    with open(fpath, "r", encoding="utf-8") as f:
        file_content = f.read()
        
    print("\n--- File Content written: ---")
    print(file_content)
    print("----------------------------\n")
    
    print("Decoding steganographic signature from file content...")
    soul = decode_soul(file_content)
    if soul:
        print("✅ SUCCESS: Decoded signature found!")
        print(f"   Agent: {soul.get('agent')}")
        if soul.get('agent') == "CoderAG":
            print("🎉 Steganographic Tracing verification: PASSED!")
        else:
            print("❌ Steganographic Tracing verification: FAILED (Wrong agent name).")
    else:
        print("❌ FAILED: No signature decoded from file.")
        sys.exit(1)
        
    # Cleanup
    if os.path.exists(fpath):
        os.unlink(fpath)
        if os.path.exists(fpath + ".bak"):
            os.unlink(fpath + ".bak")

if __name__ == "__main__":
    main()
