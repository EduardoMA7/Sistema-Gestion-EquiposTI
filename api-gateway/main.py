from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import httpx
import os

app = FastAPI(title="IT Equipment Management API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICE_URLS = {
    "equipment": "http://equipment-service:8001",
    "providers": "http://provider-service:8002",
    "maintenance": "http://maintenance-service:8003",
    "reports": "http://report-service:8004"
}

DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"

client = httpx.AsyncClient()

@app.middleware("http")
async def forward_request(request: Request, call_next):
    path_parts = request.url.path.strip("/").split("/")

    if not path_parts:
        return await call_next(request)

    service_name = path_parts[0]

    if service_name not in SERVICE_URLS:
        return await call_next(request)

    target_url = f"{SERVICE_URLS[service_name]}{request.url.path}"

    try:
        headers = dict(request.headers)
        headers["host"] = target_url.split("//")[1].split("/")[0]

        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=request.query_params,
            content=await request.body()
        )

        content_type = response.headers.get("content-type", "").lower()

        forward_headers = dict(response.headers)
        forward_headers.pop("content-encoding", None)
        forward_headers.pop("transfer-encoding", None)
        forward_headers.pop("connection", None)

        if "application/json" in content_type or "application/problem+json" in content_type:
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code,
                headers=forward_headers
            )
        else:
            return Response(
                content=response.content,
                status_code=response.status_code,
                media_type=content_type or "application/octet-stream",
                headers=forward_headers
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service {service_name} is unavailable: {str(e)}"
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)