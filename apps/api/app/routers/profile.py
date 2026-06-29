from fastapi import APIRouter, Depends, HTTPException, status
from app.core.deps import get_current_user_id, get_supabase
from app.schemas.profile import ProfileUpdate
from supabase import Client

router = APIRouter()


@router.get("")
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    result = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
    if result.data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="프로필이 없습니다.")
    return result.data


@router.put("")
async def update_profile(
    body: ProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="변경할 필드가 없습니다.")

    result = (
        supabase.table("user_profiles")
        .upsert({"id": user_id, **payload})
        .execute()
    )
    return result.data
