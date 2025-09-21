import os, sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/../src"))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
from tools.registry import ToolRegistry

if __name__ == "__main__":
    tr = ToolRegistry()
    tr.build_tools()
    keys = sorted(tr.list_tools().keys())
    print("LOADED", len(keys))
    for k in keys:
        print(k)
    for name in ["kimi_upload_and_extract", "kimi_multi_file_chat", "glm_upload_file"]:
        try:
            t = tr.get_tool(name)
            print(f"GET {name}: OK -> {type(t).__name__}")
        except Exception as e:
            print(f"GET {name}: ERROR -> {e}")

