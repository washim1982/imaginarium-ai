from fastapi import APIRouter, HTTPException, Request
from app.services import ollama_service as ollama
from app.services.training_service import train_sql_model, train_custom_model, save_pairs_to_file


router = APIRouter(prefix="/api/training", tags=["Training"])


@router.post("/sql-trainer")
async def sql_trainer(request: Request):
    try:
        body = await request.json()
        schema = body.get("schema")
        count = body.get("count")
        save = bool(body.get("save", False))
        save_format = (body.get("format") or "json").lower()
        if not schema:
            raise HTTPException(status_code=400, detail="Schema is required")
        try:
            c = int(count) if count is not None else None
        except Exception:
            c = None
        result = await train_sql_model(schema, c, placeholders=True)
        payload = {"pairs": result}
        if save:
            try:
                file_path = save_pairs_to_file(result, fmt=save_format)
                payload["file_name"] = file_path
            except Exception as e:
                # Do not fail the whole call if save fails; just return pairs
                payload["save_error"] = str(e)
        return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lora")
async def train_lora(request: Request):
    try:
        body = await request.json()
        base_model = body.get("base_model")
        new_model = body.get("new_model")
        file_name = body.get("file_name") or body.get("training_file")

        if not base_model or not new_model:
            raise HTTPException(status_code=400, detail="Missing parameters")

        # Reuse the existing training simulator. We treat the base model name as the
        # training file placeholder when none is provided.
        result = await train_custom_model(new_model, file_name or base_model)
        adapter_path = None
        message = result
        if isinstance(result, dict):
            message = result.get("message")
            adapter_path = result.get("adapter_path")
        # Try to create/overwrite the Ollama tag so it can be used immediately.
        created = ollama.create_model_tag(new_model, base_model, adapter_path)
        return {"model": new_model, "message": message, "create": created}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train-model")
async def train_model(request: Request):
    try:
        body = await request.json()
        model_name = body.get("model_name")
        file_name = body.get("file_name")
        if not model_name or not file_name:
            raise HTTPException(status_code=400, detail="Missing parameters")
        result = await train_custom_model(model_name, file_name)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ensure-model")
async def ensure_model(request: Request):
    body = await request.json()
    base_model = body.get("base_model")
    new_model = body.get("new_model")
    adapter_path = body.get("adapter_path")
    if not base_model or not new_model:
        raise HTTPException(status_code=400, detail="Missing parameters")
    res = ollama.ensure_model_tag(new_model, base_model, adapter_path)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("detail"))
    return {"ok": True, "detail": res.get("detail")}
