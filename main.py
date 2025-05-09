import os
import zipfile
import shutil
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from tempfile import mkdtemp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCKERFILE_TEMPLATE = '''
FROM python:3.10-slim
WORKDIR /app
COPY . /app
{install_commands}
CMD ["python", "{entry_point}"]
'''

DOCKER_COMPOSE_TEMPLATE = '''
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - .:/app
    command: ["python", "{entry_point}"]
'''

def extract_zip(uploaded_file: UploadFile, extract_to: str):
    try:
        temp_file_path = os.path.join(extract_to, "temp.zip")
        with open(temp_file_path, "wb") as temp_file:
            chunk_size = 1024 * 1024
            while chunk := uploaded_file.file.read(chunk_size):
                temp_file.write(chunk)

        with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

        os.remove(temp_file_path)

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting zip: {str(e)}")
    finally:
        try:
            uploaded_file.file.seek(0)
        except:
            pass

def find_project_root(extract_dir: str) -> str:
    items = os.listdir(extract_dir)
    dirs = [item for item in items if os.path.isdir(os.path.join(extract_dir, item))]

    if len(dirs) == 1 and (len(items) == 1 or (len(items) == 2 and "temp.zip" in items)):
        potential_root = os.path.join(extract_dir, dirs[0])
        if any(os.path.exists(os.path.join(potential_root, file)) 
               for file in ["app.py", "requirements.txt", "pyproject.toml"]):
            return potential_root

    return extract_dir

def find_entry_point(project_path: str):
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(".py"):
                try:
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        content = f.read()
                        if "if _name_ == '_main_'" in content:
                            rel_path = os.path.relpath(file_path, project_path)
                            return rel_path
                except:
                    continue

    common_files = ["app.py", "main.py", "server.py", "api.py", "run.py", "wsgi.py"]
    for filename in common_files:
        file_path = os.path.join(project_path, filename)
        if os.path.exists(file_path):
            return filename

    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(".py"):
                try:
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        content = f.read().lower()
                        if "from flask import" in content or "import flask" in content or \
                           "from fastapi import" in content or "import fastapi" in content:
                            rel_path = os.path.relpath(file_path, project_path)
                            return rel_path
                except:
                    continue

    return "app.py"

def generate_dockerfile(project_path: str):
    requirements_file = os.path.join(project_path, "requirements.txt")
    install_commands = ""

    if os.path.exists(requirements_file) and os.path.getsize(requirements_file) > 0:
        install_commands = "RUN pip install --no-cache-dir -r requirements.txt"

    entry_point = find_entry_point(project_path)

    dockerfile_content = DOCKERFILE_TEMPLATE.format(
        install_commands=install_commands,
        entry_point=entry_point.replace("\\", "/")
    )

    return dockerfile_content, entry_point

def generate_docker_compose(entry_point: str):
    return DOCKER_COMPOSE_TEMPLATE.format(
        entry_point=entry_point.replace("\\", "/")
    )

@app.post("/generate-dockerfile")
async def generate(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        return JSONResponse(
            status_code=400, 
            content={"error": "File must be a ZIP archive"}
        )

    temp_dir = mkdtemp()
    try:
        extract_zip(file, temp_dir)
        project_root = find_project_root(temp_dir)
        dockerfile_content, entry_point = generate_dockerfile(project_root)
        docker_compose_content = generate_docker_compose(entry_point)

        response = {
            "dockerfile": dockerfile_content,
            "docker_compose": docker_compose_content,
            "entry_point": entry_point,
            "build_command": "docker build -t myapp .",
            "run_command": "docker run -p 5000:5000 myapp",
            "docker_compose_command": "docker-compose up",
        }

        return JSONResponse(content=response)
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"Error: {error_msg}")
        return JSONResponse(
            status_code=500, 
            content={"error": f"An error occurred: {str(e)}"}
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.get("/")
async def root():
    return {"message": "Welcome to the Dockerfile and Docker Compose Generator API!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)