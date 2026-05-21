from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Warehouse Flow"
    api_prefix: str = "/api"
    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'warehouse.db').as_posix()}"
    purchase_workbook: Path = PROJECT_DIR / "采购" / "物料采购清单列表0226.xlsx"
    warehouse_workbook: Path = PROJECT_DIR / "仓库" / "仓库库存2026最新版_备注并入规格型号.xlsx"
    feishu_app_id: str | None = None
    feishu_app_secret: str | None = None
    feishu_purchase_approval_code: str | None = None
    feishu_open_api_base_url: str = "https://open.feishu.cn/open-apis"
    feishu_approval_api_base_url: str = "https://www.feishu.cn/approval/openapi/v2"
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()

