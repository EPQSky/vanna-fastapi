import logging
import os
import asyncio
from typing import Dict, Any

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from chromadb.utils import embedding_functions
from pydantic import BaseModel

from loggings import get_logger, log_config
from custom_vanna import LocalContext_OpenAI

# 配置日志
logging.config.dictConfig(log_config)
logger = get_logger()

app = FastAPI()

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 读取环境变量并打印配置信息
logger.info("=== 初始化配置 ===")
logger.info(f"推理接口: {os.environ.get('INFERENCE_URL') or '使用OpenAI兼容接口'}")
logger.info(f"模型: {os.environ.get('MODEL', '默认')}")

# 统一的数据库配置变量名
db_type = os.environ.get('DB_TYPE', 'mysql').lower()  # 默认使用mysql
db_host = os.environ.get('DB_HOST')
db_port = int(os.environ.get('DB_PORT', 3306))  # MySQL默认端口3306，PostgreSQL默认端口5432
db_name = os.environ.get('DB_NAME')
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')

logger.info(f"数据库类型: {db_type}")
logger.info(f"数据库: {db_host}:{db_port}/{db_name}")
logger.info("================")

vn = LocalContext_OpenAI(
    config={
        # 允许LLM看到查到的数据
        # "allow_llm_to_see_data": True,
        
        # 自定义推理接口配置（/v1/completions 接口）
        "inference_url": os.environ.get("INFERENCE_URL"),  # 例如: https://your-ip:your-port/v1/completions
        "inference_headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('API_KEY')}" if os.environ.get('API_KEY') else "",
        },
        
        # 如果没有指定inference_url，则回退到OpenAI兼容接口
        "api_key": os.environ.get("API_KEY"),
        "base_url": os.environ.get("BASE_URL"),
        "model": os.environ.get("MODEL"),
        "temperature": float(os.environ.get("TEMPERATURE", "0.7")),
        "top_p": float(os.environ.get("TOP_P", "1.0")),
        
        # 向量存储配置
        "path": "chroma_db",
        "embedding_function": embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ.get("EMBED_API_KEY"),
            api_base=os.environ.get("EMBED_API_BASE"),
            model_name=os.environ.get("EMBED_MODEL_NAME"),
        ),
    }
)

# 根据数据库类型连接对应的数据库
if db_type == 'postgres' or db_type == 'postgresql':
    logger.info("连接到PostgreSQL数据库...")
    vn.connect_to_postgres(
        host=db_host,
        dbname=db_name,
        user=db_user,
        password=db_password,
        port=db_port,
    )
elif db_type == 'mysql':
    logger.info("连接到MySQL数据库...")
    vn.connect_to_mysql(
        host=db_host,
        dbname=db_name,
        user=db_user,
        password=db_password,
        port=db_port,
    )
else:
    logger.error(f"不支持的数据库类型: {db_type}")
    raise ValueError(f"不支持的数据库类型: {db_type}。支持的类型: mysql, postgres/postgresql")

logger.info("Vanna初始化完成")


async def process_text_to_sql(question: str) -> Dict[str, Any]:
    """处理文本到SQL的转换，包含超时和错误处理"""
    try:
        logger.info(f"开始处理问题: {question}")

        # 生成SQL
        logger.info("开始生成SQL...")
        sql = await asyncio.wait_for(
            asyncio.to_thread(vn.generate_sql, question=question),
            timeout=60,  # 60秒超时
        )
        logger.info(f"生成的SQL: {sql}")

        # 执行SQL
        logger.info("开始执行SQL...")
        df = await asyncio.wait_for(
            asyncio.to_thread(vn.run_sql, sql=sql), timeout=30  # 30秒超时
        )
        logger.info(f"查询结果行数: {len(df)}")

        return {"type": "df", "df": df.head(10).to_json(orient="records"), "sql": sql}

    except asyncio.TimeoutError:
        logger.error(f"处理问题超时: {question}")
        raise HTTPException(status_code=408, detail="请求处理超时，请稍后重试")
    except Exception as e:
        logger.error(f"处理问题时发生错误: {question}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理请求时发生错误: {str(e)}")


@app.get("/api/v0/text-to-sql")
async def text_to_sql(question: str = Query(..., description="用户输入的文本")):
    return await process_text_to_sql(question)


@app.get("/api/v0/get_training_data")
async def get_training_data():
    try:
        logger.info("获取训练数据...")
        df = await asyncio.wait_for(asyncio.to_thread(vn.get_training_data), timeout=30)

        return {
            "type": "df",
            "id": "training_data",
            "df": df.head(25).to_json(orient="records"),
        }
    except asyncio.TimeoutError:
        logger.error("获取训练数据超时")
        raise HTTPException(status_code=408, detail="获取训练数据超时")
    except Exception as e:
        logger.error(f"获取训练数据时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取训练数据失败: {str(e)}")


@app.post("/api/v0/remove_training_data")
async def remove_training_data(id: str = Query(..., description="训练数据ID")):
    try:
        logger.info(f"删除训练数据: {id}")
        result = await asyncio.wait_for(
            asyncio.to_thread(vn.remove_training_data, id=id), timeout=30
        )

        if result:
            return {"success": True}
        else:
            raise HTTPException(status_code=400, detail="无法删除训练数据")
    except asyncio.TimeoutError:
        logger.error(f"删除训练数据超时: {id}")
        raise HTTPException(status_code=408, detail="删除训练数据超时")
    except Exception as e:
        logger.error(f"删除训练数据时发生错误: {id}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除训练数据失败: {str(e)}")


class TrainingData(BaseModel):
    question: str | None = None
    sql: str | None = None
    ddl: str | None = None
    documentation: str | None = None


@app.post("/api/v0/train")
async def add_training_data(training_data: TrainingData):
    try:
        logger.info(f"添加训练数据: {training_data.question}")
        training_id = await asyncio.wait_for(
            asyncio.to_thread(
                vn.train,
                question=training_data.question,
                sql=training_data.sql,
                ddl=training_data.ddl,
                documentation=training_data.documentation,
            ),
            timeout=60,
        )
        return {"id": training_id}
    except asyncio.TimeoutError:
        logger.error("添加训练数据超时")
        raise HTTPException(status_code=408, detail="添加训练数据超时")
    except Exception as e:
        logger.error(f"添加训练数据时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加训练数据失败: {str(e)}")



