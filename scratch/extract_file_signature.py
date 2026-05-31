# extract_file_signature.py — Forensic utility to extract steganographic agent metadata from files
import sys, os

# Add project root and src directory to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from gnom_hub.soul.zwc_soul import decode_soul

def main():
    if len(sys.argv) < 2:
        print("❌ Usage: python3 scratch/extract_file_signature.py <file_path>")
        sys.exit(1)
        
    fpath = sys.argv[1]
    if not os.path.exists(fpath):
        print(f"❌ Error: File '{fpath}' not found.")
        sys.exit(1)
        
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        soul = decode_soul(content)
        if soul:
            print("============================================================")
            print(" 🕵️‍♂️ GNOM-HUB STEGANOGRAPHIC SIGNATURE FOUND!")
            print("============================================================")
            for k, v in soul.items():
                print(f" • {k.capitalize()}: {v}")
            print("============================================================")
        else:
            print("🔍 No agent steganographic signature found in this file.")
            
    except Exception as e:
        print(f"❌ Error reading file: {e}")

if __name__ == "__main__":
    main()
