import uvicorn

if __name__ == "__main__":
    # Standard Uvicorn bootstrapper for the FastAPI application
    print("Starting Gluzo Backend on http://localhost:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
