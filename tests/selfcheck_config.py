import os
import sys
import traceback
from vacsim.config.io import load_config

def main():
    try:
        print("Starting config test...")
        
        # Check if file exists
        config_path = "configs/experiments/example.yaml"
        if not os.path.exists(config_path):
            print(f"❌ Config file not found: {config_path}")
            print(f"Current directory: {os.getcwd()}")
            try:
                print(f"Files in configs/experiments/: {os.listdir('configs/experiments/')}")
            except:
                print("Could not list directory contents")
            return
            
        print(f"Loading config from: {config_path}")
        cfg = load_config(config_path)

        print("✅ Config loaded successfully")
        print("type_mix:", getattr(cfg.task, "type_mix", None))
        print("policy.params:", getattr(cfg.policy, "params", None))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
