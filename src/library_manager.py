import os
import subprocess
from pathlib import Path

# Configuration
LIBS_DIR = Path("libs")
LIBRARIES = {
    "kicad-symbols": "https://gitlab.com/kicad/libraries/kicad-symbols.git",
    "kicad-footprints": "https://gitlab.com/kicad/libraries/kicad-footprints.git",
    "alternate-kicad-library": "https://github.com/DawidCislo/Alternate-KiCad-Library.git",
    "freetronics-kicad-library": "https://github.com/freetronics/freetronics_kicad_library.git"
}

def setup_libs_dir():
    if not LIBS_DIR.exists():
        print(f"Creating libraries directory: {LIBS_DIR}")
        LIBS_DIR.mkdir(parents=True, exist_ok=True)

def clone_or_pull_repo(name, url):
    repo_path = LIBS_DIR / name
    if repo_path.exists():
        print(f"Updating {name}...")
        subprocess.run(["git", "pull"], cwd=repo_path, check=False)
    else:
        print(f"Cloning {name}...")
        # Deep clone might be huge. Using depth=1 for speed and space saving.
        subprocess.run(["git", "clone", "--depth", "1", url, str(repo_path)], check=True)

def main():
    setup_libs_dir()
    print("Starting library setup...")
    for name, url in LIBRARIES.items():
        try:
            clone_or_pull_repo(name, url)
            print(f"Successfully processed {name}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing {name}: {e}")
            
    print("Library setup complete.")

if __name__ == "__main__":
    main()
