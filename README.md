# Vanna FastAPI - 智能文本转SQL服务

一个基于 Vanna AI 的智能文本转SQL查询服务，支持自然语言查询数据库，提供FastAPI接口和向量检索增强功能。

## 🚀 项目特性

- **智能文本转SQL**：使用自然语言查询数据库，自动生成SQL语句
- **多数据库支持**：支持 MySQL 和 PostgreSQL 数据库
- **双推理模式**：支持自定义推理接口和OpenAI兼容接口
- **向量检索增强**：基于ChromaDB的向量存储，提升SQL生成准确性
- **训练数据管理**：支持添加、查看、删除训练数据来优化模型表现
- **异步处理**：支持异步请求处理，防止超时
- **完整日志**：详细的日志记录和错误处理
- **Docker部署**：提供完整的Docker容器化部署方案

## 📋 技术栈

- **后端框架**：FastAPI 0.115.12
- **AI引擎**：Vanna AI 0.7.9
- **向量数据库**：ChromaDB
- **支持数据库**：MySQL、PostgreSQL
- **Web服务器**：Gunicorn + Uvicorn
- **容器化**：Docker
- **Python版本**：3.11+

## 🛠️ 环境配置

### 必需的环境变量

```bash
# 数据库配置（必需）
DB_TYPE=mysql                    # 数据库类型：mysql 或 postgres/postgresql
DB_HOST=your-database-host       # 数据库主机地址
DB_NAME=your-database-name       # 数据库名称
DB_USER=your-username           # 数据库用户名
DB_PASSWORD=your-password       # 数据库密码
DB_PORT=3306                    # 数据库端口（MySQL默认3306，PostgreSQL默认5432）

# 向量嵌入配置（必需）
EMBED_API_KEY=your-embed-api-key          # 嵌入模型API密钥
EMBED_API_BASE=https://api.example.com/v1  # 嵌入模型API基础URL
EMBED_MODEL_NAME=your-embed-model          # 嵌入模型名称

# 推理配置（二选一）
# 方案1：使用自定义推理接口（/v1/completions格式）
INFERENCE_URL=https://your-ip:port/v1/completions

# 方案2：使用OpenAI兼容接口（/v1/chat/completions格式）
BASE_URL=https://api.example.com/v1

# 通用配置
API_KEY=your-api-key            # API密钥
MODEL=your-model-name           # 模型名称
TEMPERATURE=0.7                 # 生成温度（0.0-1.0）
TOP_P=1.0                      # Top-p采样参数
```

### 配置说明

#### 推理接口配置

**自定义推理接口（/v1/completions）**
- 如果设置了 `INFERENCE_URL`，系统将使用自定义推理接口
- 接口需要兼容OpenAI Completions API格式

**OpenAI兼容接口（/v1/chat/completions）**
- 如果没有设置 `INFERENCE_URL`，系统将使用OpenAI兼容接口
- 通过 `BASE_URL` 指定API基础地址

#### 数据库配置

支持的数据库类型：
- `mysql`：MySQL数据库
- `postgres` 或 `postgresql`：PostgreSQL数据库

## 🔌 API接口文档

### 1. 文本转SQL查询

**接口地址**：`GET /api/v0/text-to-sql`

**功能**：将自然语言问题转换为SQL查询并执行

**参数**：
- `question` (string, 必需)：用户输入的自然语言问题

**请求示例**：
```bash
GET /api/v0/text-to-sql?question=有多少个用户
```

**响应示例**：
```json
{
  "type": "df",
  "df": "[{\"count\": 150}]",
  "sql": "SELECT COUNT(*) as count FROM users;"
}
```

**响应字段**：
- `type`：响应类型，固定为"df"
- `df`：查询结果的JSON格式数据（最多返回10行）
- `sql`：生成的SQL语句

---

### 2. 获取训练数据

**接口地址**：`GET /api/v0/get_training_data`

**功能**：获取当前的训练数据列表

**响应示例**：
```json
{
  "type": "df",
  "id": "training_data",
  "df": "[{\"id\": \"abc-123\", \"question\": \"示例问题\", \"sql\": \"SELECT * FROM table;\"}]"
}
```

**响应字段**：
- `type`：响应类型，固定为"df"
- `id`：数据标识，固定为"training_data"
- `df`：训练数据的JSON格式列表（最多返回25条）

---

### 3. 添加训练数据

**接口地址**：`POST /api/v0/train`

**功能**：添加新的训练数据来改善模型表现

**请求体**：
```json
{
  "question": "有多少个活跃用户？",
  "sql": "SELECT COUNT(*) FROM users WHERE status = 'active';",
  "ddl": "CREATE TABLE users (id INT, name VARCHAR(100), status VARCHAR(20));",
  "documentation": "用户表包含所有注册用户信息"
}
```

**请求字段**：
- `question` (string, 可选)：问题描述
- `sql` (string, 可选)：对应的SQL语句
- `ddl` (string, 可选)：数据定义语句
- `documentation` (string, 可选)：文档说明

**响应示例**：
```json
{
  "id": "generated-training-id"
}
```

---

### 4. 删除训练数据

**接口地址**：`POST /api/v0/remove_training_data`

**功能**：删除指定的训练数据

**参数**：
- `id` (string, 必需)：要删除的训练数据ID

**请求示例**：
```bash
POST /api/v0/remove_training_data?id=abc-123-def-456
```

**响应示例**：
```json
{
  "success": true
}
```

## 🚀 部署指南

### Docker部署（推荐）

1. **构建镜像**：
```bash
docker build -t vanna-fastapi:latest .
```

2. **创建环境配置文件** `.env`：
```bash
# 数据库配置
DB_TYPE=mysql
DB_HOST=your-db-host
DB_NAME=your-database
DB_USER=your-username
DB_PASSWORD=your-password
DB_PORT=3306

# API配置
API_KEY=your-api-key
BASE_URL=https://api.siliconflow.cn/v1
MODEL=Qwen/Qwen3-32B
TEMPERATURE=0.7
TOP_P=0.8

# 嵌入配置
EMBED_API_KEY=your-embed-key
EMBED_API_BASE=https://api.siliconflow.cn/v1
EMBED_MODEL_NAME=BAAI/bge-m3
```

3. **运行容器**：
```bash
docker run -d \
  --name vanna-fastapi \
  --env-file .env \
  -p 8000:5000 \
  -v $(pwd)/chroma_db:/app/chroma_db \
  vanna-fastapi:latest
```

### Docker Compose部署

使用提供的 `docker-compose.yaml`：

```bash
# 修改docker-compose.yaml中的环境变量
# 然后运行
docker-compose up -d
```

### 本地开发部署

1. **安装依赖**：
```bash
pip install -r requirements.txt
```

2. **设置环境变量**：
```bash
export DB_TYPE=mysql
export DB_HOST=localhost
# ... 其他环境变量
```

3. **运行服务**：
```bash
# 开发模式
uvicorn main:app --reload --host 0.0.0.0 --port 5000

# 生产模式
gunicorn main:app -c gunicorn_config.py
```

## 📝 使用示例

### Python客户端示例

```python
import requests

# 基础URL
BASE_URL = "http://localhost:8000"

# 文本转SQL查询
def query_database(question):
    response = requests.get(
        f"{BASE_URL}/api/v0/text-to-sql",
        params={"question": question}
    )
    return response.json()

# 添加训练数据
def add_training_data(question, sql):
    response = requests.post(
        f"{BASE_URL}/api/v0/train",
        json={"question": question, "sql": sql}
    )
    return response.json()

# 使用示例
result = query_database("显示所有用户的数量")
print(f"SQL: {result['sql']}")
print(f"结果: {result['df']}")
```

### cURL示例

```bash
# 查询示例
curl -X GET "http://localhost:8000/api/v0/text-to-sql?question=有多少个用户"

# 添加训练数据
curl -X POST "http://localhost:8000/api/v0/train" \
  -H "Content-Type: application/json" \
  -d '{"question": "用户总数", "sql": "SELECT COUNT(*) FROM users;"}'

# 删除训练数据
curl -X POST "http://localhost:8000/api/v0/remove_training_data?id=your-training-id"
```

## 📊 日志和监控

### 日志文件

- `logs/app.log`：应用程序日志
- `logs/error.log`：错误日志
- `logs/access.log`：访问日志

### 日志配置

- 日志自动按天轮转
- 保留30天历史日志
- 支持日志压缩

## ⚙️ 自定义推理接口

如果使用自定义推理接口，需要实现兼容以下格式的 `/v1/completions` 接口：

**请求格式**：
```json
{
  "prompt": "System: 你是一个SQL专家\nHuman: 查询用户数量\nAssistant:",
  "model": "your-model",
  "temperature": 0.7,
  "top_p": 1.0,
  "max_tokens": 2048,
  "stop": null
}
```

**响应格式**：
```json
{
  "choices": [
    {
      "text": "SELECT COUNT(*) FROM users;"
    }
  ]
}
```

## 🔧 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库配置参数
   - 确认数据库服务正在运行
   - 验证网络连接

2. **API调用超时**
   - 检查推理接口URL是否正确
   - 验证API密钥是否有效
   - 确认网络连接稳定

3. **向量嵌入失败**
   - 检查嵌入模型配置
   - 验证嵌入API密钥
   - 确认嵌入服务可用性

### 调试模式

启用详细日志：
```bash
export LOG_LEVEL=DEBUG
```

## 📚 更多信息

- 在线API文档：访问 `http://localhost:8000/docs` 查看Swagger文档
- Vanna AI官方文档：https://docs.vanna.ai/
- FastAPI文档：https://fastapi.tiangolo.com/

## 📄 许可证

本项目采用 MIT 许可证。详情请参阅 LICENSE 文件。
