# compile_production_gnom.py — Compiles a real SuperGNOM from the current active state
import sys, os

# Add project root and src directory to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from gnom_hub.core.utils.compiler import bake_supergnom

def main():
    name = "prod_gnom"
    print(f"🏭 Starting compilation for SuperGNOM: '{name}'...")
    try:
        dist_dir = bake_supergnom(name, template="chat")
        print("============================================================")
        print(" 🎉 SUPERGNOM COMPILED SUCCESSFULLY!")
        print("============================================================")
        print(f" • Name:        {name}")
        print(f" • Location:    {dist_dir}")
        print(f" • Run Script:  {os.path.join(dist_dir, 'run.sh')}")
        print("============================================================")
        print("💡 You can navigate to the location and execute './run.sh'")
        print("   to start your standalone, frozen SuperGNOM on port 3003!")
    except Exception as e:
        print(f"❌ Compilation failed: {e}")

if __name__ == "__main__":
    main()
