from fastapi import FastAPI
import uvicorn
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from director_assistant import Assistant

# 初始化FastAPI应用
app = FastAPI(title="Director Assistant API", version="1.0")

# 初始化智能体
assistant = Assistant()

@app.get("/")
def read_root():
    return {"message": "欢迎访问Director Assistant智能体服务", "status": "运行中"}

@app.post("/assistant/query")
def process_query(query: str):
    """处理用户查询并返回智能体响应"""
    response = assistant.process(query)
    return {"query": query, "response": response}

if __name__ == "__main__":
    # 使用Uvicorn在8031端口启动服务
    uvicorn.run(
        app="acps_endpoint:app",
        host="0.0.0.0",
        port=8031,
        reload=True  # 开发模式下自动重载
    )