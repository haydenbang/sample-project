"""상품 API 스키마."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.product import ProductStatus


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=50)
    price: int = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    brand_id: int | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=50)
    price: int | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    status: ProductStatus | None = None
    brand_id: int | None = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ProductStatus


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    size: int