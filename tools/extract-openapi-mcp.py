import json
import yaml
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Convert OpenAPI JSON paths to custom YAML format")
parser.add_argument("file", type=str, help="Path to openapi.json")
parser.add_argument("-o", "--output", type=str, help="Output YAML file")
parser.add_argument("-p", "--prompt_output", type=str, help="Output prompts.json file")
parser.add_argument("-s", "--server_url", type=str, required=True, help="MCP Server URL, e.g. 192.168.40.112:38002/zabbix")
args = parser.parse_args()

SERVER_URL = args.server_url

def convert_openapi_paths_to_yaml(json_file: str):
    json_file = Path(json_file)
    if not json_file.exists():
        raise FileNotFoundError(f"File not found: {json_file}")

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []

    paths = data.get("paths", {})

    for path, methods in paths.items():
        for method, info in methods.items():
            # doc_name: 去掉前綴 /mars_ 和 method 後綴
            doc_name = path.lstrip("/") + "_doc"

            # content: 優先 summary，其次 description
            content = info.get("description") or info.get("summary") or "No description."

            results.append({
                "doc_name": doc_name,
                "content": content,
                "endpoint": path,
                "server_name": SERVER_URL
            })

    return yaml.dump(results, sort_keys=False, allow_unicode=True)

def convert_openapi_to_prompts(json_file: str):
    json_file = Path(json_file)
    if not json_file.exists():
        raise FileNotFoundError(f"File not found: {json_file}")

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompts = []
    paths = data.get("paths", {})

    for path, methods in paths.items():
        for method, info in methods.items():

            prompts.append({
                "command": path,
                "title": info.get("summary"),
                "content": info.get('description')
            })

    return prompts

def main():
    # YAML
    yaml_text = convert_openapi_paths_to_yaml(args.file)
    if not yaml_text.strip():
        print("⚠️  No paths found.")
        return

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(yaml_text)
        print(f"✅ YAML exported to: {args.output}")
    else:
        print(yaml_text)


    # Prompts
    prompts = convert_openapi_to_prompts(args.file)
    if args.prompt_output:
        with open(args.prompt_output, "w", encoding="utf-8") as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)
        print(f"✅ Prompts JSON exported to: {args.prompt_output}")
    else:
        print("--- prompts.json ---")
        print(json.dumps(prompts, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
