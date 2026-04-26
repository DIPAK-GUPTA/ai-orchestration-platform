"""Tools registry route"""
from fastapi import APIRouter
from app.agents.tools import AVAILABLE_TOOLS

router = APIRouter()


@router.get("")
async def list_tools():
    return AVAILABLE_TOOLS
