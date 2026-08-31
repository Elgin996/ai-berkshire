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

    print("=== 开始安装 Skills: investment-agy & technical-analysis ===")
    
    for skill_name in TARGET_SKILLS:
        src = os.path.join(CODEX_SKILLS_DIR, skill_name)
        if not os.path.isdir(src):
            print(f"❌ 找不到源技能目录: {src}")
            continue

        # Copy to Workspace .agents/skills/
        dst_workspace = os.path.join(workspace_agents_dir, skill_name)
        if os.path.exists(dst_workspace):
            shutil.rmtree(dst_workspace)
        shutil.copytree(src, dst_workspace)
        print(f"✅ [Workspace] 已安装到工作区: {dst_workspace}")

        # Copy to Global ~/.gemini/config/skills/
        dst_gemini = os.path.join(global_gemini_skills, skill_name)
        if os.path.exists(dst_gemini):
            shutil.rmtree(dst_gemini)
        shutil.copytree(src, dst_gemini)
        print(f"✅ [Global Gemini/Antigravity] 已安装到全局配置: {dst_gemini}")

        # Copy to Global ~/.codex/skills/
        dst_codex = os.path.join(global_codex_skills, skill_name)
        if os.path.exists(dst_codex):
            shutil.rmtree(dst_codex)
        shutil.copytree(src, dst_codex)
        print(f"✅ [Global Codex] 已安装到 Codex 全局目录: {dst_codex}")

    print("\n🎉 安装完成！Antigravity 在当前工作区以及全局环境中均可随时发现并调用这两项 Skill。")

if __name__ == "__main__":
    install_skills()
