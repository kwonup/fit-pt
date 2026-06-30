from fastapi import APIRouter, Depends, HTTPException, status
from postgrest.exceptions import APIError
from app.core.deps import get_current_user_id, get_supabase
from app.schemas.profile import ProfileUpdate
from supabase import Client

router = APIRouter()


def _is_no_rows_error(exc: APIError) -> bool:
    error = exc.args[0] if exc.args else {}
    return isinstance(error, dict) and error.get("code") == "PGRST116"


@router.get("")
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    try:
        result = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
    except APIError as exc:
        if _is_no_rows_error(exc):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="프로필이 없습니다.") from exc
        raise
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
