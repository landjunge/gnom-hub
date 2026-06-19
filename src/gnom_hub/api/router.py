from fastapi import APIRouter
from .endpoints.router import router as endpoints_router

router = APIRouter()
router.include_router(endpoints_router)
