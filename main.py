from fastapi import FastAPI

app = FastAPI(title="Garage")


@app.get("/")
def root():
    return {"message": "Garage работает"}