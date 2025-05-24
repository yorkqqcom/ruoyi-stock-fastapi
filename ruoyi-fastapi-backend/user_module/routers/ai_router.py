from fastapi import APIRouter,  HTTPException,Body
from mcp.client.sse import sse_client
from pydantic import BaseModel
import httpx
from utils.response_util import ResponseUtil
from typing import Optional, List  # 新增导入
import asyncio
from contextlib import asynccontextmanager

from user_module.services.stock_hist_service import StockHistService
import json
import os
from typing import  Any
from mcp import ClientSession
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path="ai.env")

class ChatResponse(BaseModel):
    response: str
    mcp_status: int = 200  # MCP协议状态码

ai_router = APIRouter(prefix="/api/ai", tags=["AI对话"])

class AIConfig:
    API_KEY = os.getenv("AI_API_KEY")
    MODEL_NAME = os.getenv("MODEL", "gpt-3.5-turbo")  # 默认值
    BASE_URL = os.getenv("BASE_URL")

# 初始化OpenAI客户端
oai_client = OpenAI(
    base_url=AIConfig.BASE_URL,
    api_key=AIConfig.API_KEY,
)

class McpServerManager:
    def __init__(self):
        self.servers = [
            {
                "id": "stock_service_1",
                "name": "股票分析服务",
                "url": "http://localhost:8000/sse",
                "category": "financial",
                "status": "offline"
            }
        ]
        self.status_check_timeout = 5  # 状态检查超时时间（秒）
    
    @asynccontextmanager
    async def _timeout_context(self, timeout: float):
        try:
            async with asyncio.timeout(timeout):
                yield
        except asyncio.TimeoutError:
            raise Exception("服务器状态检查超时")
    
    async def check_server_status(self, server_url: str) -> str:
        try:
            async with self._timeout_context(self.status_check_timeout):
                async with sse_client(server_url) as (read, write):
                    async with ClientSession(read, write) as mcp_session:
                        await mcp_session.initialize()
                        return "online"
        except Exception as e:
            print(f"服务器状态检查失败: {str(e)}")
            return "offline"
    
    async def update_all_servers_status(self):
        tasks = []
        for server in self.servers:
            task = asyncio.create_task(self.check_server_status(server["url"]))
            tasks.append((server, task))
        
        for server, task in tasks:
            try:
                status = await task
                server["status"] = status
            except Exception as e:
                print(f"更新服务器 {server['id']} 状态失败: {str(e)}")
                server["status"] = "offline"

class HybridAgent:
    def __init__(self):
        self.mcp_servers = [
            {"name": "stock_service",
             "url": "http://localhost:8000/sse",
             "category": "financial"}
        ]

    async def execute_query(self, question: str, model: str = None, selected_tools: Optional[List[str]] = None):
        model = model or AIConfig.MODEL_NAME
        openai_tools = []
        tool_registry = {}

        # 1. 连接所有服务并收集工具（带过滤功能）
        for server in self.mcp_servers:
            try:
                async with sse_client(server["url"]) as (read, write):
                    async with ClientSession(read, write) as mcp_session:
                        await mcp_session.initialize()
                        tools = await mcp_session.list_tools()
                        for tool in tools.tools:
                            # 工具名称过滤逻辑
                            # if selected_tools and tool.name not in selected_tools:
                            #     continue

                            schema = tool.inputSchema
                            if not isinstance(schema, dict):
                                continue
                            if schema.get("type") != "object":
                                continue
                            if not isinstance(schema.get("properties"), dict):
                                continue

                            # 强制转换参数类型为JSON Schema兼容类型
                            required_fields = []
                            properties = {}
                            for param_name, param_schema in schema["properties"].items():
                                if not isinstance(param_schema, dict):
                                    continue

                                # 处理类型字段
                                param_type = param_schema.get("type", "string")
                                if param_type not in ["string", "number", "integer", "boolean", "object", "array"]:
                                    param_type = "string"  # 设置默认类型

                                # 处理必填字段
                                if param_schema.get("required", False):
                                    required_fields.append(param_name)

                                properties[param_name] = {
                                    "type": param_type,
                                    "description": param_schema.get("description", "")
                                }

                            # 构建符合规范的schema
                            validated_schema = {
                                "type": "object",
                                "properties": properties
                            }
                            if required_fields:
                                validated_schema["required"] = required_fields

                            openai_tools.append({
                                "type": "function",
                                "function": {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "parameters": validated_schema
                                }
                            })
                            tool_registry[tool.name] = {
                                "server_url": server["url"],
                                "service_name": server["name"],
                                "service_category": server["category"]
                            }

            except Exception as e:
                print(f"连接服务 {server['name']} 失败: {str(e)}")
                continue

        if not openai_tools:
            return "没有可用的服务工具"

        # 处理选中的工具情况
        if selected_tools:
            print('selected_tools',selected_tools)
            # 过滤出可用的选中工具
            available_tools = [t for t in openai_tools if t['function']['name'] in selected_tools]
            if not available_tools:
                return "选中的工具不可用"
            # 遍历每个选中的工具并执行
            available_tool_names = [t['function']['name'] for t in available_tools]
            all_tool_calls = []
            all_results = []
            for tool_name in available_tool_names:
                print('tool_name', tool_name)
                current_tool_choice = {
                    "type": "function",
                    "function": {"name": tool_name}
                }
                # 单次调用模型生成所有工具调用
                response = oai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": question}],
                    tools=available_tools,
                    tool_choice=current_tool_choice
                )
                message = response.choices[0].message
                tool_calls = getattr(message, 'tool_calls', [])

                # 执行所有工具调用
                tool_results = []
                for tool_call in tool_calls:
                    result = await self._execute_single_tool(tool_call, tool_registry)
                    tool_results.append((tool_call, result))

            # 构建正确的消息结构
            final_messages = [
                {"role": "user", "content": question},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            },
                            "type": "function"
                        } for tc in tool_calls
                    ]
                }
            ]
            for tool_call, result in tool_results:
                final_messages.append({
                    "role": "tool",
                    "content": json.dumps(result),
                    "tool_call_id": tool_call.id
                })
            print('final_messages',len(final_messages),final_messages)
            # 生成最终响应
            final_response = oai_client.chat.completions.create(
                model=model,
                messages=final_messages
            )
            return final_response.choices[0].message.content

        else:
            # 原有自动选择工具逻辑
            print('openai_tools', openai_tools)
            response = oai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": question}],
                tools=openai_tools,
                tool_choice="auto"  # 自动选择工具
            )

            if not response.choices:
                return "模型未返回有效响应"

            message = response.choices[0].message
            tool_calls = getattr(message, 'tool_calls', None)
            print('tool_calls', tool_calls)
            if tool_calls:
                tool_results = []
                for tool_call in tool_calls:

                    result = await self._execute_single_tool(tool_call, tool_registry)
                    print(tool_call, result)
                    tool_results.append((tool_call, result))

                messages = self.build_messages(question, tool_calls, tool_results)

                final_response = oai_client.chat.completions.create(
                    model=model,
                    messages=messages
                )
                return final_response.choices[0].message.content
            else:
                return message.content

    async def _execute_single_tool(self, tool_call, tool_registry):
        tool_name = tool_call.function.name

        if tool_name not in tool_registry:
            return {"error": f"工具 {tool_name} 未注册"}

        server_info = tool_registry[tool_name]
        try:
            args = json.loads(tool_call.function.arguments)
            if server_info["service_category"] == "financial":
                args = await self._preprocess_financial_args(args)

            async with sse_client(server_info["server_url"]) as (read, write):
                async with ClientSession(read, write) as mcp_session:
                    await mcp_session.initialize()
                    # 假设call_tool需要JSON字符串参数
                    result = await mcp_session.call_tool(tool_name, args)
                    print(tool_name,result)
                    return {"content": str(result), "status": "success"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    async def _preprocess_financial_args(self, args):
        # if 'symbol' in args and not args['symbol'].isdigit():
        #     # 假设get_stock_list是异步方法
        #     df = await StockHistService.get_stock_list()
        #     exact_match = df[df['name'] == args['symbol']]
        #     if not exact_match.empty:
        #         args['symbol'] = exact_match.iloc[0]['symbol']
        #     else:
        #         fuzzy_match = df[df['name'].str.contains(args['symbol'], na=False)]
        #         if not fuzzy_match.empty:
        #             args['symbol'] = fuzzy_match.iloc[0]['symbol']
        #         else:
        #             raise ValueError(f"无效的股票代码: {args['symbol']}")
        return args

    def build_messages(self, question, tool_calls, results):
        messages = [
            {"role": "user", "content": question},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        },
                        "type": "function"
                    } for tc in tool_calls
                ]
            }
        ]
        for (tool_call, result) in results:
            messages.append({
                "role": "tool",
                "content": json.dumps(result),  # 确保内容为字符串
                "tool_call_id": tool_call.id
            })
        return messages

class ChatRequest(BaseModel):
    query: str
    model: str = "qwen-plus-latest"
    stream: bool = False
    temperature: float = 0.7
    tools: Optional[List[str]] = None  # 新增工具选择字段

@ai_router.post("/chat")
async def chat(
        request: ChatRequest = Body(...)
):
    try:
        print('selected_tools', request.tools)
        response = await call_llm(
            query=request.query,
            model=request.model,
            stream=request.stream,
            temperature=request.temperature,
            selected_tools=request.tools  # 传递工具参数
        )

        return ResponseUtil.success(data=ChatResponse(
            response=response,
            mcp_status=200
        ))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "response": f"处理失败: {str(e)}",
                "mcp_status": 500
            }
        )

async def call_llm(
        query: str,
        model: str = "qwen-plus-latest",
        stream: bool = False,
        temperature: float = 0.7,
        selected_tools: Optional[List[str]] = None  # 新增参数
):
    try:
        agent = HybridAgent()
        result = await agent.execute_query(
            query,
            model=model,
            selected_tools=selected_tools  # 传递工具参数
        )
        return result
    except httpx.HTTPStatusError as http_err:
        raise HTTPException(
            status_code=http_err.response.status_code,
            detail={"response": "HTTP错误", "mcp_status": 500}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"response": str(e), "mcp_status": 500}
        )