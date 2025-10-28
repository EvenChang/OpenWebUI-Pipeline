"""
title: Ollama RAG Pipeline
author: even
date: 2025-09-11
version: 1.1
license: MIT
description: A Manifold RAG pipeline integrating Chroma for semantic search and Ollama-based LLMs.
             Supports multi-model routing, conversation memory, and intelligent API recovery by using
             the LLM to infer or request missing parameters when an MCP API call fails .
requirements: llama-index-core==0.12.16, pydantic==2.8.0, langchain-community==0.4, langchain-huggingface==1.0.0, langchain-chroma==1.0.0, sentence-transformers, faiss-cpu, requests
"""
from typing import List, Union, Generator, Iterator

from openai import OpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import BaseModel, Field
import os, requests, json
# from langchain.memory import ConversationBufferWindowMemory

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

from langchain_chroma import Chroma
from chromadb.config import Settings

class Pipeline:
    class Valves(BaseModel):
        MCPO_SERVER_API_KEY: str = Field(default="eventest",
                                         description="MCPO Server API KEY, e.g. 'apikey'")
        OPENAI_BASE_URL: str = Field(default="http://192.168.42.200:11434/v1",
                                     description="OpenAI base URL, e.g. 'http://192.168.42.200:11434/v1'")
        OPENAI_API_KEY: str = Field(default="ollama",
                                    description="OpenAI API key, e.g. 'ollama'."
                                                "If use Ollama the OpenAI API key is required but unused.")
        MODEL: str = Field(default="llama3.2:latest", description="Model name, e.g. 'gpt-oss:20b'")

        CHROMA_DB_SERVER: str = Field(default="192.168.40.112", description="ChromaDB Server address, e.g. '192.168.40.112'")
        CHROMA_DB_USERNAME: str = Field(default="admin", description="ChromaDB Username")
        CHROMA_DB_PASSWORD: str = Field(default="admin", description="ChromaDB Password")

    def __init__(self):

        # Initialize valve parameters
        self.valves = self.Valves(
            **{k: os.getenv(k, v.default) for k, v in self.Valves.model_fields.items()}
        )

        self.vector_store = None
        self.memory = InMemoryChatMessageHistory()

        self.type = "manifold"   # 宣告這是一個「多路」管線
        self.name = "Manifold: " # UI 上顯示的名稱 prefix

        self.pipelines = [
            {"id": "ollama", "name": "Ollama"},
            {"id": "deepseek", "name": "DeepSeek"},
            {"id": "openai", "name": "OpenAI"},
        ]

    async def on_startup(self):
        print("on-startup")
        try:
            embedding = HuggingFaceEmbeddings(model_name="DMetaSoul/Dmeta-embedding-zh-small")

            settings = Settings(
                chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
                chroma_client_auth_credentials="my-secret-token",
            )

            self.vector_store = Chroma(
                collection_name="documents_api_collection",
                embedding_function=embedding,
                host=self.valves.CHROMA_DB_SERVER,
                port=7777,
                client_settings=settings,
            )
            print("on_startup")

        except Exception as e:
            print(f"on_startup 執行錯誤: {e}")
            return f"發生錯誤: {e}"

    async def on_shutdown(self):
        pass


    LOGIN_PATH = "/api/login"
    SERVERS_PATH = "/api/servers"

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:

        print("model_id:", model_id)

        if model_id == "ollama":
            try:
                print("pipe called")
                if self.vector_store is None:
                    return "⚠️ 向量索引尚未初始化，無法搜尋知識庫。"


                retrieved_docs = self.vector_store.similarity_search_with_score(user_message, k=1)
                print("retrieved_docs:", retrieved_docs)

                if not retrieved_docs:
                    return str(self.call_original_llm(user_message))

                doc, score = retrieved_docs[0]
                if score > 0.75:
                    print(f"相似度太低 ({score})，跳過 RAG，直接交給 LLM")
                    return str(self.call_original_llm(user_message))

                api_path = doc.metadata["endpoint"]
                server_name = doc.metadata["server_name"]
                url = self.get_server_url(server_name)
                print("url:", url)

                payload = body.get("payload", {})  # 假設你讓 UI 傳 payload
                response = self.call_api(api_path, payload, user_message, url)


                if isinstance(response, (dict, list)):
                    def response_generator(data):
                        yield "```json\n"
                        pretty_json = json.dumps(data, ensure_ascii=False, indent=2)
                        for line in pretty_json.splitlines():
                            yield line + "\n"
                        yield "```"

                    return response_generator(response)  # 回傳 generator

                return str(response)

            except Exception as e:
                print(f"Exception : {e}")
                return str(self.call_original_llm(user_message))

        return f"LLM {model_id} not supported"


    def call_original_llm(self, user_message: str):
        self.memory.clear()
        client = OpenAI(
            base_url=self.valves.OPENAI_BASE_URL,
            api_key=self.valves.OPENAI_API_KEY,  # required, but unused
        )

        system_prompt = "You are a ChatGPT, answer the user's questions"
        messages = [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}]

        resp = client.chat.completions.create(
            model=self.valves.MODEL,
            messages=messages,
            temperature=0,
        )

        llm_content = resp.choices[0].message.content
        # self.memory.chat_memory.add_user_message(user_message)
        # self.memory.chat_memory.add_ai_message(llm_content)
        print("call original LLM : ", llm_content)

        return llm_content

    def call_llm(self, system_prompt: str, user_message: str, server_url: str):

        client = OpenAI(
            base_url=self.valves.OPENAI_BASE_URL,
            api_key=self.valves.OPENAI_API_KEY,  # required, but unused
        )
        history  = self.memory.messages[-2:]
        # history = self.memory.load_memory_variables({}).get("history", [])
        print("Chat history : ", history)

        messages = [{"role": "system", "content": system_prompt}]

        for msg in history:
            if isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages.append({"role": "assistant", "content": msg.content})

        messages.append({"role": "user", "content": user_message})

        resp = client.chat.completions.create(
            model=self.valves.MODEL,
            messages=messages,
            temperature=0,
        )

        try:
            if resp and resp.choices and len(resp.choices) > 0:
                llm_content = resp.choices[0].message.content
                print("llm_content:", llm_content)

                self.memory.add_message(HumanMessage(content=user_message))
                self.memory.add_message(AIMessage(content=llm_content))

                # self.memory.chat_memory.add_user_message(user_message)
                # self.memory.chat_memory.add_ai_message(llm_content)

                try:
                    parsed_content = json.loads(llm_content)

                    if "missing_params" in parsed_content:
                        return parsed_content

                    if "api" in parsed_content and "params" in parsed_content:
                        api_path = parsed_content["api"]
                        payload = parsed_content.get("params", {})
                        response_status_code, response_json = self.call_llm_api(api_path, payload, server_url)
                        if response_status_code == 200:
                            return response_json

                    # if content is not recognized then direct to original LLM to answer user's questions.
                    return self.call_original_llm(user_message)

                except Exception as e:
                    print(f"Exception : {e}")
                    return self.call_original_llm(user_message)

        except Exception as e:
            return f"Exception : {e}"

    def call_llm_api(self, api_path, payload=None, server_url=None):

        print("call llm api")
        url = server_url + api_path
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.valves.MCPO_SERVER_API_KEY
        }
        payload = payload or {}
        print("url: " + url , "headers: ", headers , "payload: ", payload)

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            print(f"response.json : {response.json()}")
            return response.status_code, response.json()

        return response.status_code, None

    def call_api(self, api_path, payload=None, user_message=None, server_url=None):

        if not api_path.startswith("/"):
            api_path = "/" + api_path

        url = server_url + api_path
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.valves.MCPO_SERVER_API_KEY
        }

        print("url:", url)
        payload = payload or {}
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"response.json : {response.json()}")
            return response.json()


        # If the API returns a 422 (missing parameters):
        # 1. Parse the error JSON and extract the missing fields.
        # 2. Ask the LLM to analyze whether these parameters can be inferred from the conversation history.
        #    - If all required params are found, return:
        #        { "api": "<api_path>", "params": { "<param>": "<value>", ... } }
        #    - If not enough info, return:
        #        { "missing_params": ["<param1>", "<param2>", ...], "message": "Please provide these parameters." }
        try:
            error_data = response.json()
            if response.status_code == 422 and "detail" in error_data:
                print("detail:", error_data["detail"])
                system_prompt = (
                    f"You are a smart assistant that helps the user call an MCP API.\n"
                    "Analyze the 'detail' message to figure out if the context has arguments for the API.\n"
                    f"API path: {api_path}\n"
                    f"Error data: {json.dumps(error_data)}\n"
                    "Your task:\n"
                    "1. If you can infer all required parameters, return JSON in the format:\n"
                    '{ "api": "<api_path>", "params": {"<param_name>": "<value>"}} \n'
                    "2. If you cannot infer the parameter values, DO NOT return empty strings or placeholders(like '', 'N/A', or '<unknown>').\n"
                    "   Instead, return JSON in this format:\n"
                    '{ "missing_params": ["<param1>", "<param2>", ...], "message": "Please provide these parameters." }\n'
                    "Rules:\n"
                    "- Never invent or guess parameter values.\n"
                    "- Never return empty string values.\n"
                    "- Only return valid JSON (no markdown, no explanation).\n"
                )

                ollama_response = self.call_llm(system_prompt, user_message, server_url)
                print(f"ollama_response: {ollama_response}")
                return ollama_response
            else:
                response = error_data.get("detail", {})
                return response

        except Exception as e:
            print(f"Exception : {e}, {response.text}")

        return self.call_original_llm(user_message)


    def get_access_token(self):
        url = f"http://{self.valves.CHROMA_DB_SERVER}/api/login"
        data = {"username": self.valves.CHROMA_DB_USERNAME, "password": self.valves.CHROMA_DB_PASSWORD}
        resp = requests.post(url, data=data)
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not token:
            raise RuntimeError("登入失敗，未取得 access_token")
        return token

    def get_servers(self, token):
        url = f"http://{self.valves.CHROMA_DB_SERVER}/api/servers"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json().get("servers", [])

    def get_server_url(self, server):
        token = self.get_access_token()
        servers = self.get_servers(token)
        for s in servers:
            if s.get("server_name") == server:
                return s.get("server_url")
        return None
