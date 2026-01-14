from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import sys
import time
from agents.hello_world.hello_world_agent import hello_world_agent

# 创建FastAPI实例
app = FastAPI()

# 配置：证书存储目录（自动创建）
CERT_UPLOAD_FOLDER = 'certs'
if not os.path.exists(CERT_UPLOAD_FOLDER):
    os.makedirs(CERT_UPLOAD_FOLDER)

# 允许上传的证书文件格式（可根据需求扩展）
ALLOWED_EXTENSIONS = {'pem', 'cer', 'crt', 'key', 'pfx'}

# 验证文件格式
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 核心接口：接收证书上传并运行自定义代码
@app.post('/challenge')
async def upload_cert(cert_file: UploadFile = File(...)):
    try:
        # 检查文件扩展名
        if not allowed_file(cert_file.filename):
            raise HTTPException(status_code=400, detail="不支持的文件格式")

        # 保存文件到服务器
        file_path = os.path.join(CERT_UPLOAD_FOLDER, cert_file.filename)
        with open(file_path, "wb") as f:
            f.write(await cert_file.read())
        print(f"证书文件已保存：{file_path}")

        # 调用自定义Python代码处理证书（核心步骤）
        # 这里根据需求修改：例如解析证书、验证有效性、执行业务逻辑等

        # 返回处理结果给外部设备
        return {
            "status": "success",
            "message": "证书上传并处理成功",
            "file_path": file_path,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"处理失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败：{str(e)}")

# 健康检查接口（可选，用于测试服务是否正常运行）
@app.get('/health')
async def health_check():
    return {
        "status": "running",
        "message": "服务正常"
    }

@app.get('/')
async def index():
    return {
        "status": "success",
        "message": "证书上传服务已启动",
        "available_apis": [
            {
                "path": "/upload-cert",
                "method": "POST",
                "description": "上传证书文件",
                "params": {"cert_file": "证书文件（支持.pem/.cer/.crt等）"}
            },
            {
                "path": "/health",
                "method": "GET",
                "description": "服务健康检查"
            }
        ]
    }

# 处理 favicon.ico 请求，返回空响应（避免404）
@app.get('/favicon.ico')
async def favicon():
    return JSONResponse(content="", status_code=204)

@app.get('/list-certs')
async def list_certs():
    try:
        # 检查certs文件夹是否存在
        if not os.path.exists(CERT_UPLOAD_FOLDER):
            return {
                "status": "success",
                "message": "证书文件夹为空",
                "file_count": 0,
                "files": []
            }

        # 遍历文件夹，获取文件详情
        file_list = []
        for filename in os.listdir(CERT_UPLOAD_FOLDER):
            # 排除文件夹（只显示文件）
            file_path = os.path.join(CERT_UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                # 获取文件大小（单位：KB）
                file_size = round(os.path.getsize(file_path) / 1024, 2)
                # 获取文件最后修改时间（格式化）
                modify_time = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(os.path.getmtime(file_path))
                )
                # 添加文件信息到列表
                file_list.append({
                    "filename": filename,
                    "size_kb": file_size,
                    "modify_time": modify_time,
                    "file_path": file_path
                })

        # 按修改时间倒序排序（最新的文件在前面）
        file_list.sort(key=lambda x: x["modify_time"], reverse=True)

        return {
            "status": "success",
            "message": f"found {len(file_list)} certificates",
            "file_count": len(file_list),
            "files": file_list
        }

    except Exception as e:
        print(f"列出文件失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"列出文件失败：{str(e)}")

# 新增：无参数触发智能体（直接访问链接就运行）
@app.get('/hello')
async def hello():
    try:
        print("开始运行智能体...")
        
        # 调用智能体核心逻辑
        agent_result = hello_world_agent()
        
        print("智能体运行完成")
        return {
            "status": "success",
            "message": "智能体运行成功",
            "agent_result": agent_result
        }

    except Exception as e:
        print(f"智能体运行失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"智能体运行失败：{str(e)}")

if __name__ == '__main__':
    import uvicorn
    # 配置uvicorn服务器，端口改为8000
    uvicorn.run(app, host='0.0.0.0', port=8000)