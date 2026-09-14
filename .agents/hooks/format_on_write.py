import sys
import json
import os
import shutil
import subprocess


def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input) if raw_input else {}
    except Exception:
        data = {}

    tool_call = data.get('toolCall', {})
    args = tool_call.get('args', {})
    file_path = args.get('TargetFile') or args.get('file_path') or ''
    normalized = file_path.replace('\\', '/')

    workspace_paths = data.get('workspacePaths') or []
    root = workspace_paths[0] if workspace_paths else os.getcwd()

    try:
        if '/backend/' in normalized and normalized.endswith('.py'):
            if os.path.isdir(os.path.join(root, 'backend')) and shutil.which('ruff'):
                subprocess.run(['ruff', 'check', '--fix', file_path], capture_output=True)
                subprocess.run(['ruff', 'format', file_path], capture_output=True)
        elif '/frontend/' in normalized and (normalized.endswith('.ts') or normalized.endswith('.tsx')):
            frontend_dir = os.path.join(root, 'frontend')
            if os.path.isfile(os.path.join(frontend_dir, 'package.json')) and shutil.which('npx'):
                subprocess.run(['npx', '--no-install', 'eslint', '--fix', file_path], cwd=frontend_dir, capture_output=True)
                subprocess.run(['npx', '--no-install', 'prettier', '--write', file_path], cwd=frontend_dir, capture_output=True)
    except Exception:
        pass

    print(json.dumps({}))


if __name__ == '__main__':
    main()
