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
    file_path = args.get('TargetFile') or args.get('file_path') or ''

    normalized = file_path.lower().replace('\\', '/')

    if re.search(r'(^|/)srs_doc/', normalized):
        output = {
            "decision": "deny",
            "reason": "SRS_Doc/ is the source-of-truth spec and must never be edited by any agent."
        }
        print(json.dumps(output))
        return

    print(json.dumps({"decision": "allow"}))


if __name__ == '__main__':
    main()
