# Linux Docker 运行说明

本项目已经补齐 Linux Docker 运行所需的基础文件，推荐使用 `docker compose` 启动前后端双容器。

当前 Docker 方案采用“前后端同源访问”模型：

- 浏览器统一访问前端容器 `http://localhost:8080`
- 前端通过同源 `/api` 请求后端
- 默认按根路径 `/` 部署，不是子路径部署方案

## 端口

- 前端入口：`http://localhost:8080`
- 后端调试与健康检查：`http://localhost:8000`
- 健康检查接口：`http://localhost:8000/health`

正常使用建议访问 `8080`，`8000` 主要用于调试和健康检查。

## 启动前准备

1. 在 Linux 主机上准备这些目录：

```bash
mkdir -p backend/data backend/logs 采购/uploaded 仓库
```

2. 确认以下 Excel 模板文件已经存在，文件名必须完全一致：

- `采购/物料采购清单列表0226.xlsx`
- `仓库/仓库库存2026最新版_备注并入规格型号.xlsx`

3. 复制环境变量示例文件并填写管理员密码和令牌密钥：

```bash
cp .env.docker.example .env.docker
```

至少要修改这两项：

- `AUTH_ADMIN_PASSWORD`
- `AUTH_TOKEN_SECRET`

飞书采购同步需要再补：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_PURCHASE_APPROVAL_CODE`

## 启动

推荐使用环境文件启动：

```bash
docker compose --env-file .env.docker up -d --build
```

后端容器启动前会做预检，以下情况会直接启动失败并打印明确错误：

- `AUTH_ADMIN_PASSWORD` 未配置
- `AUTH_TOKEN_SECRET` 未配置
- Excel 模板文件缺失
- 必需工作表缺失
- SQLite / 日志 / Excel 目录不可写

## 停止

```bash
docker compose down
```

## 挂载目录说明

- `./backend/data`：SQLite 数据目录，首次启动后会生成 `warehouse.db`
- `./backend/logs`：运行日志目录
- `./采购`：采购 Excel 模板和上传归档目录
- `./仓库`：仓库 Excel 模板目录

这些目录会直接挂载进容器，所以容器内外会共用同一份数据和模板文件。要注意一件事：如果宿主机上的 `采购/` 或 `仓库/` 是空目录，它会覆盖镜像里自带的模板文件，所以正式启动前一定要先把模板文件放到宿主机目录里。

## 启动后验证

```bash
docker compose ps
curl http://127.0.0.1:8000/health
```

如果健康检查正常，再打开浏览器访问：

```text
http://localhost:8080
```

## 说明

- 前端容器使用 `nginx` 提供静态页面，并将 `/api` 反向代理到后端容器。
- `nginx` 已放宽 Excel 上传大小与长时间 API 请求超时，适配采购导入和飞书同步场景。
- 后端容器使用 `uvicorn` 启动 FastAPI，并在启动时自动初始化 SQLite 表结构。
- `docker compose` 已增加后端健康检查，前端会等待后端健康后再启动。
- SQLite 建库建表不等于业务数据已初始化。库存、采购、导出模板仍依赖挂载目录中的 Excel 文件。
