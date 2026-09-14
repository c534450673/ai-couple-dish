"""目录模型的兼容导出。

持久化模型由 ``app.db.models`` 集中声明，避免每个微服务持有同一张表的不同映射。
"""

from app.db.models import CatalogCuisine as Cuisine
from app.db.models import CatalogDish as DishRecord
from app.db.models import CatalogDishImage as DishImage
from app.db.models import CatalogDishSource, CatalogImportBatch

__all__ = ["CatalogDishSource", "CatalogImportBatch", "Cuisine", "DishImage", "DishRecord"]
