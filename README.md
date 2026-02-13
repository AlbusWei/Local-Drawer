# Nano Banana Pro Local WebUI

这是一个便于使用的本地画图WebUI，基于Nano Banana Pro (Gemini 3 Pro Image) API构建。

## 功能特性

- 🎨 **文生图**: 输入提示词生成高质量图片
- 🔄 **图生图**: 支持拖拽上传参考图片
- 🖼️ **历史画廊**: 自动保存生成记录，随时查看
- ⚡ **本地存储**: 图片和记录全部保存在本地，安全隐私
- 🛠️ **自定义API**: 支持自定义API网关和Base URL

## 🚀 快速启动

### macOS / Linux

1.  赋予脚本执行权限：
    ```bash
    chmod +x start.sh
    ```
2.  运行启动脚本：
    ```bash
    ./start.sh
    ```

### Windows

1.  双击运行 `start.bat` 脚本。
    *   脚本会自动检测并创建 Python 虚拟环境。
    *   自动安装 Python 和 Node.js 依赖。
    *   分别在两个新窗口中启动后端和前端服务。

### 手动启动

### 1. 安装依赖

确保你已经安装了 `python3` 和 `node`。

```bash
# 安装后端依赖
pip3 install -r backend/requirements.txt

# 安装前端依赖
cd frontend
npm install
cd ..
```

### 2. 启动应用

运行启动脚本即可同时启动前后端服务：

```bash
./start.sh
```

- 前端地址: http://localhost:5173
- 后端地址: http://localhost:8000

## 配置说明

后端配置位于 `backend/main.py`，你可以修改以下常量：

- `API_KEY`: 你的API密钥
- `BASE_URL`: API Base URL (默认为 https://right.codes/gemini/v1beta/)
- `GENERATED_IMAGES_DIR`: 生成图片保存路径
- `HISTORY_FILE`: 历史记录文件路径

## 技术栈

- **Frontend**: React, Vite, TailwindCSS, Lucide Icons
- **Backend**: FastAPI, Google GenAI SDK
- **Storage**: Local File System

## 开发与测试

运行后端测试：

```bash
export PYTHONPATH=$PYTHONPATH:.
python3 -m pytest tests/test_api.py
```
