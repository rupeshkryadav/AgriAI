import os
import io
import logging
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from ..ai_service import diagnose_leaf, chat_with_gemini

router = APIRouter(prefix="/api/ai-doctor", tags=["AI Doctor"])
logger = logging.getLogger(__name__)


async def _run_ai(operation, *args):
    try:
        return await operation(*args)
    except HTTPException:
        raise
    except Exception as exc:
        # Keep unexpected SDK/runtime failures in the AI Doctor API contract
        # instead of returning FastAPI's unhelpful generic 500 response.
        logger.error("AI Doctor provider call failed (%s).", type(exc).__name__)
        raise HTTPException(502, "AI Doctor could not reach Gemini. Please retry shortly.") from exc

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    language: str = "Auto-detect"
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)

@router.post("")
async def diagnose(image: UploadFile = File(...), language: str = Form("English")):
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Upload a JPEG, PNG, or WEBP leaf photo.")
    content = await image.read()
    if not content or len(content) > int(os.getenv("MAX_UPLOAD_MB", "8")) * 1024 * 1024:
        raise HTTPException(413, "Image is empty or exceeds the upload limit.")
    try:
        with Image.open(io.BytesIO(content)) as decoded:
            actual_mime={"JPEG":"image/jpeg","PNG":"image/png","WEBP":"image/webp"}.get(decoded.format)
            decoded.verify()
    except (UnidentifiedImageError,OSError) as exc:
        raise HTTPException(422,"Upload a valid JPEG, PNG, or WEBP leaf photo.") from exc
    if actual_mime!=image.content_type:
        raise HTTPException(415,"Image content does not match its declared MIME type.")
    return await _run_ai(diagnose_leaf, content, image.content_type, language)

@router.post("/chat")
async def chat(payload: ChatRequest):
    return await _run_ai(chat_with_gemini, payload.message, payload.language, payload.history)
