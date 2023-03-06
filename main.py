from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello, that's a Soul AI Bot!"}


@app.get("/health")
async def health():
    return {"status": "ok"}
