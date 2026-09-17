"""
Web API endpoint for scam detection fallback
This is used when local model fails or is uncertain
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from local_llm import LocalScamClassifier
import asyncio

app = FastAPI()

class ScamRequest(BaseModel):
    transcript: str

classifier = LocalScamClassifier()

@app.on_event("startup")
async def startup():
    print("Loading scam classifier...")
    classifier.load_model()
    print("Classifier loaded successfully!")

@app.post("/predict")
async def predict(request: ScamRequest):
    try:
        result = await classifier.predict_instant_scam(request.transcript)
        return {
            "is_scam": result["is_scam"],
            "category": result["category"],
            "reasoning": result.get("reasoning", ""),
            "confidence": 0.9 if result["is_scam"] else 0.1
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": classifier.model is not None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
