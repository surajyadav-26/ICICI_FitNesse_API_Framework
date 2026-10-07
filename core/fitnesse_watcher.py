import os
import time
import sys

def heal_workspace():
    frontpage_dir = "FitNesseRoot/FrontPage"
    if not os.path.exists(frontpage_dir):
        return
        
    for file in os.listdir(frontpage_dir):
        # 1. If we find a flat .wiki file that represents a suite page
        if file.endswith(".wiki"):
            name = file.replace(".wiki", "")
            name_lower = name.lower()
            
            # Skip actual test pages, only heal high-level suites!
            is_suite = "suite" in name_lower or "regression" in name_lower or "smoke" in name_lower or "sanity" in name_lower or "demo" in name_lower
            
            if is_suite:
                wiki_file_path = os.path.join(frontpage_dir, file)
                folder_path = os.path.join(frontpage_dir, name)
                
                # Delete flat .wiki file
                try:
                    if os.path.exists(wiki_file_path):
                        os.remove(wiki_file_path)
                except Exception:
                    continue
                    
                # Create proper directory folder
                os.makedirs(folder_path, exist_ok=True)
                
                # Write properties.xml with <Suite/>
                properties_xml = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<properties>
  <Suite/>
  <Edit/>
  <Files/>
  <Properties/>
  <RecentChanges/>
  <Refactor/>
  <Search/>
  <Versions/>
  <WhereUsed/>
</properties>
"""
                with open(os.path.join(folder_path, "properties.xml"), "w", encoding="utf-8") as f:
                    f.write(properties_xml)
                    
                # Write content.txt containing !contents macro
                with open(os.path.join(folder_path, "content.txt"), "w", encoding="utf-8") as f:
                    f.write("!contents -R2 -g -p -h\n")
                print(f"[WATCHER] Self-healed flat suite file into folder: {name}")

    # 2. Heal any empty content.txt files inside Suite folders
    for root, dirs, files in os.walk(frontpage_dir):
        for file in files:
            if file == "content.txt":
                content_file_path = os.path.join(root, file)
                properties_file_path = os.path.join(root, "properties.xml")
                
                # If properties.xml contains <Suite/> (meaning it's a Suite page!)
                if os.path.exists(properties_file_path):
                    try:
                        with open(properties_file_path, "r", encoding="utf-8") as f:
                            props = f.read()
                        if "<Suite/>" in props:
                            # Read content
                            with open(content_file_path, "r", encoding="utf-8") as f:
                                content = f.read().strip()
                            # If empty or missing !contents, heal it!
                            if content == "" or "!contents" not in content:
                                with open(content_file_path, "w", encoding="utf-8") as f:
                                    f.write("!contents -R2 -g -p -h\n")
                                print(f"[WATCHER] Self-healed empty suite contents: {content_file_path}")
                    except Exception:
                        continue

def main():
    print("[WATCHER] Real-Time FitNesse Folder-Sync Self-Healing Watcher started.")
    sys.stdout.flush()
    while True:
        try:
            heal_workspace()
        except Exception:
            pass
        time.sleep(0.5) # Fast 500ms check loop!

if __name__ == "__main__":
    main()
