import uvicorn

from seed.generate import build


if __name__ == "__main__":
    build()
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000)
