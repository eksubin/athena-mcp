from pydantic import BaseModel


class PlotOut(BaseModel):
    user_id: str
    username: str
    avatar_seed: str
    origin_x: int
    origin_y: int


class StructureOut(BaseModel):
    id: str
    user_id: str
    type: str
    grid_x: int
    grid_y: int
