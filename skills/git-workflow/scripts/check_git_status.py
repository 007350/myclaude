"""
Helper script for git-workflow skill: check dirty working tree and show uncommitted files
"""
import subprocess
import sys


def main():
    try:
        res = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, check=True)
        output = res.stdout.strip()
        if not output:
            print("✅ Git 工作区非常干净，无任何未提交修改。")
        else:
            print("⚠️ 检测到以下未提交或未追踪文件:")
            print(output)
    except Exception as e:
        print(f"❌ 运行 git status 失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
