from typing import Annotated, Optional, List
from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, Field, ConfigDict

PyObjectId = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, ObjectId) else v)]


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    @classmethod
    def from_mongo(cls, doc):
        return cls.model_validate(doc) if doc else None

    def to_mongo(self) -> dict:
        d = self.model_dump(by_alias=True, exclude={"id"})
        if self.id:
            d["_id"] = ObjectId(self.id)
        return d


class User(BaseDocument):
    email: str
    name: str
    role: str = "user"
    password_hash: Optional[str] = None
    created_at: str

    def public(self) -> dict:
        return self.model_dump(exclude={"password_hash"})


class CollectionItem(BaseDocument):
    user_id: str
    card_id: str
    set_id: Optional[str] = None
    set_name: Optional[str] = None
    name: str
    local_id: Optional[str] = None
    local_num: Optional[int] = None
    image: Optional[str] = None
    rarity: Optional[str] = None
    category: Optional[str] = None
    types: List[str] = []
    variant: str = "normal"
    quantity: int = 1
    condition: str = "NM"
    price_usd: Optional[float] = None
    price_eur: Optional[float] = None
    created_at: str
    updated_at: str
