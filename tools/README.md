## Introduction
The purpose of `extract-openapi-mcp.py` is to extract essential fields from an openapi.json file to generate both RAG import YAML and OpenWebUI Prompt JSON files.

## Feature
1. Generate a RAG import YAML file from `openapi.json` 
2. Generate an OpenWebUI Prompt JSON file from `openapi.json`

## How to use

1. Run the MCPO server with the following configuration
- Example MCPO Config:
```{
  "mcpServers": {
    "KubeSphere": {
      "args": [
        "stdio",
        "--ksconfig", "/home/mars/mcpServer/ecpaas-mcp-server/config",
        "--ks-apiserver", "http://192.168.40.112:30880"
      ],
      "command": "/home/mars/mcpServer/ecpaas-mcp-server/ks-mcp-server",
      "env": {
        "KUBESPHERE_CONTEXT": "kubernetes-admin@cluster.local"
      }
    },
    "mars": {
      "args": ["--mars-server-url", "http://192.168.40.135:38181"],
      "command": "/home/mars/mcpServer/mars-mcp-server/dist/mars_mcp_server"
    },
    "zabbix": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/mars/mcpServer/zabbix-mcp-server",
        "python",
        "src/zabbix_mcp_server.py"
      ],
      "env": {
        "ZABBIX_URL": "http://192.168.42.212:8080/",
        "ZABBIX_TOKEN": "8c412aba76d6c13221de15dd05123537e420a4a9b338f3889d2092d89fd8b143",
        "READ_ONLY": "true"
      }
    }
  }
}
```
- Run the MCPO server:
```
uvx mcpo --port 38002 --config config
```

2. Fetch the MCP server's OpenAPI specification
```
curl http://192.168.40.112:38002/zabbix/openapi.json > zabbix.json
```

3. Generate the RAG YAML and prompt JSON files

```
python extract-openapi-mcp.py  zabbix.json -s Zabbix -o zabbix.yaml -p zabbix_prompt.json
```

## Notes

- -s specifies the MCP server name which added on website.

- -o defines the output YAML file path for RAG import.

- -p defines the output JSON file path for OpenWebUI prompt import.



