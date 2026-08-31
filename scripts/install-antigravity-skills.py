#!/usr/bin/env python3
"""安装 Antigravity / Codex Skills 到本地工作区和全局配置目录。"""

import os
import shutil
import sys

# Reconfigure stdout for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODEX_SKILLS_DIR = os.path.join(ROOT_DIR, "codex-skills")

TARGET_SKILLS = ["investment-agy", "technical-analysis", "consensus-valuation"]

def install_skills():
    # 1. Project Workspace: .agents/skills/
    workspace_agents_dir = os.path.join(ROOT_DIR, ".agents", "skills")
    os.makedirs(workspace_agents_dir, exist_ok=True)
    
    # 2. Global Antigravity Config: ~/.gemini/config/skills/
    global_gemini_skills = os.path.expanduser("~/.gemini/config/skills")
    os.makedirs(global_gemini_skills, exist_ok=True)
    
    # 3. Global Codex Skills: ~/.codex/skills/
    global_codex_skills = os.path.expanduser("~/.codex/skills")
    os.makedirs(global_codex_skills, exist_ok=True)

    # 4. Global Agents Skills: ~/.agents/skills/
    global_agents_skills = os.path.expanduser("~/.agents/skills")
    os.makedirs(global_agents_skills, exist_ok=True)

    # 5. Global Antigravity Skills: ~/.gemini/antigravity/skills/
    global_agy_skills = os.path.expanduser("~/.gemini/antigravity/skills")
    os.makedirs(global_agy_skills, exist_ok=True)

    print("=== 开始安装 Skills 到本地工作区和所有 Antigravity 全局目录 ===")

    # Ensure consensus-valuation has bundled scripts
    cv_scripts_dir = os.path.join(CODEX_SKILLS_DIR, "consensus-valuation", "scripts")
    os.makedirs(cv_scripts_dir, exist_ok=True)
    src_tool = os.path.join(ROOT_DIR, "tools", "multi_source_valuation.py")
    if os.path.isfile(src_tool):
        shutil.copy2(src_tool, os.path.join(cv_scripts_dir, "multi_source_valuation.py"))
    
    for skill_name in TARGET_SKILLS:
        src = os.path.join(CODEX_SKILLS_DIR, skill_name)
        if not os.path.isdir(src):
            print(f"❌ 找不到源技能目录: {src}")
            continue

        targets = [
            ("Workspace", os.path.join(workspace_agents_dir, skill_name)),
            ("Global Gemini Config", os.path.join(global_gemini_skills, skill_name)),
            ("Global Codex", os.path.join(global_codex_skills, skill_name)),
            ("Global Agents", os.path.join(global_agents_skills, skill_name)),
            ("Global Antigravity AppData", os.path.join(global_agy_skills, skill_name)),
        ]

        for label, dst in targets:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"✅ [{label}] 已安装: {dst}")

    print("\n🎉 全局安装完成！Antigravity 在所有工作区及系统全局环境中均可随时直接发现并调用 consensus-valuation。")

if __name__ == "__main__":
    install_skills()
