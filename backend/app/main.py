from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    health,
    models,
    chat,
    training,
    analysis,
    ocr,
    translation,
    rag,
    code_fix,
    search,
)
from app.routers import debug_auth
from app.routers import weather


app = FastAPI(title="Imaginarium AI API")

app.add_middleware(
CORSMiddleware,
allow_origins=["*"], 
allow_credentials=True,
allow_methods=["*"], 
allow_headers=["*"],
)


# app.include_router(health.router, prefix="/api", tags=["health"])
# app.include_router(models.router, prefix="/api", tags=["models"])
# app.include_router(chat.router, prefix="/api", tags=["chat"])
# app.include_router(training.router, prefix="/api", tags=["training"])
# app.include_router(analysis.router, prefix="/api", tags=["analysis"])
# app.include_router(ocr.router, prefix="/api", tags=["ocr"])
# app.include_router(translation.router, prefix="/api", tags=["translation"])
# app.include_router(rag.router, prefix="/api", tags=["rag"])
app.include_router(health.router)
app.include_router(models.router)
app.include_router(chat.router)
app.include_router(training.router)
app.include_router(ocr.router)
app.include_router(analysis.router)
app.include_router(rag.router)
app.include_router(translation.router)
app.include_router(code_fix.router)
app.include_router(search.router)
app.include_router(weather.router)
