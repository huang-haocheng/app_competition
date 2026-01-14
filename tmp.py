# test_uvicorn.py（极简测试脚本）
from fastapi import FastAPI
import uvicorn

app = FastAPI()

# 最简单的根接口
@app.get("/")
async def root():
    return {"status": "success"}

if __name__ == "__main__":
    # 强制绑定 0.0.0.0:8032，开启 debug 日志
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8032,
        log_level="debug"
    )