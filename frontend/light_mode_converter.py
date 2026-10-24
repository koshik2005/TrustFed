import os
import re

FRONTEND_DIR = r"e:\Finalyear\frontend\src"

REPLACEMENTS = {
    "bg-[#070B14]": "bg-slate-50",
    "bg-[#0A0F1E]": "bg-slate-50",
    "bg-[#0d152599]": "bg-white/90",
    "bg-[#0F1629]": "bg-white",
    "text-white": "text-slate-900",
    "border-white/10": "border-slate-200",
    "border-white/5": "border-slate-200",
    "bg-white/5": "bg-slate-100",
    "bg-white/10": "bg-slate-200",
    "hover:bg-white/10": "hover:bg-slate-200",
    "text-slate-400": "text-slate-600",
    "text-slate-300": "text-slate-700",
    "text-slate-200": "text-slate-800",
    "bg-[#0d1525]": "bg-white",
}

def convert_to_light_mode():
    for root, _, files in os.walk(FRONTEND_DIR):
        for file in files:
            if file.endswith((".tsx", ".ts")):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                new_content = content
                for old, new in REPLACEMENTS.items():
                    new_content = new_content.replace(old, new)
                
                if new_content != content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"Updated {filepath}")

if __name__ == "__main__":
    convert_to_light_mode()
    print("Done converting React components to light mode.")
