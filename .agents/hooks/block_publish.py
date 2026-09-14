import sys
import json
import re

def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input) if raw_input else {}
    except Exception:
        data = {}

    tool_call = data.get('toolCall', {})
    args = tool_call.get('args', {})
    command = args.get('CommandLine', '') or ''

    if re.search(r'(^|[;&|\s])git\s+push(\s|$)', command, re.IGNORECASE):
        output = {
            "decision": "ask",
            "reason": "git push detected. Only approve if implementation-verifier-shipper is active and you have granted explicit approval to ship."
        }
        print(json.dumps(output))
        return

    if re.search(r'(^|[;&|\s])gh\s+pr(\s|$)', command, re.IGNORECASE):
        output = {
            "decision": "ask",
            "reason": "gh pr detected. Only approve if implementation-verifier-shipper is active and you have granted explicit approval to ship."
        }
        print(json.dumps(output))
        return

    print(json.dumps({"decision": "allow"}))

if __name__ == '__main__':
    main()
