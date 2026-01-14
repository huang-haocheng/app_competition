1. 安装必要的依赖：fastapi和uvicorn
2. 重写app.py文件，使用FastAPI替代Flask
3. 保留核心功能：

   * 证书上传接口（/challenge）

   * 健康检查接口（/health）

   * 首页信息接口（/）

   * 列出证书接口（/list-certs）

   * 无参数触发智能体接口（/hello）

   * favicon.ico处理
4. 移除导演智能体接口（/director\_assistant）
5. 修改端口为8000
6. 确保文件上传功能正常
7. 配置Uvicorn服务器运行

