import os
import json
import shutil
import zipfile
from tempfile import mkdtemp
import tempfile

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

PYTHON_DOCKERFILE_TEMPLATE = '''
FROM python:3.11-slim
WORKDIR /app
COPY . /app
{install_commands}
CMD ["python", "{entry_point}"]
'''

PYTHON_DOCKER_COMPOSE_TEMPLATE = '''
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    command: ["python", "{entry_point}"]
'''

REACT_DOCKERFILE_TEMPLATE = '''
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
{build_command}

FROM nginx:alpine
COPY --from=builder /app/{build_output} /usr/share/nginx/html
RUN echo 'server {{ \
    listen 80; \
    server_name localhost; \
    location / {{ \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    }} \
}}' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
'''

REACT_DOCKER_COMPOSE_TEMPLATE = '''
version: '3.8'

services:
  app:
    build: .
    ports:
      - "80:80"
'''

PYTHON_K8S_TEMPLATE = {
    "deployment.yaml": '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: python-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: python-app
  template:
    metadata:
      labels:
        app: python-app
    spec:
      containers:
      - name: python-app
        image: pythonapp
        ports:
        - containerPort: 5000
''',
    "service.yaml": '''
apiVersion: v1
kind: Service
metadata:
  name: python-service
spec:
  selector:
    app: python-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 5000
  type: LoadBalancer
'''
}

REACT_K8S_TEMPLATE = {
    "deployment.yaml": '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: react-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: react-app
  template:
    metadata:
      labels:
        app: react-app
    spec:
      containers:
      - name: react-app
        image: reactapp
        ports:
        - containerPort: 80
''',
    "service.yaml": '''
apiVersion: v1
kind: Service
metadata:
  name: react-service
spec:
  selector:
    app: react-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: LoadBalancer
'''
}

@app.post("/generate-docker")
async def generate_docker(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")

    temp_dir = mkdtemp()
    try:
        await extract_zip(file, temp_dir)
        project_path = find_project_root(temp_dir)
        project_type = detect_project_type(project_path)

        if project_type == "python":
            result = generate_python_dockerfile(project_path)
        else:
            result = generate_react_dockerfile(project_path)

        return JSONResponse(content={"project_type": project_type, **result})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.post("/generate-k8s")
async def generate_k8s(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")

    temp_dir = mkdtemp()
    try:
        await extract_zip(file, temp_dir)
        project_path = find_project_root(temp_dir)
        project_type = detect_project_type(project_path)

        k8s_files = PYTHON_K8S_TEMPLATE if project_type == "python" else REACT_K8S_TEMPLATE
        return JSONResponse(content={"project_type": project_type, "k8s": k8s_files})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.post("/export")
async def export(file: UploadFile = File(...), deployment_type: str = Query("docker", enum=["docker", "k8s"])):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")

    temp_dir = mkdtemp()
    try:
        await extract_zip(file, temp_dir)
        project_path = find_project_root(temp_dir)
        project_type = detect_project_type(project_path)

        export_dir = os.path.join(temp_dir, "export_bundle")
        shutil.copytree(project_path, export_dir, dirs_exist_ok=True)

        if deployment_type == "docker":
            result = generate_python_dockerfile(project_path) if project_type == "python" else generate_react_dockerfile(project_path)
            with open(os.path.join(export_dir, "Dockerfile"), "w") as df:
                df.write(result["dockerfile"])
            with open(os.path.join(export_dir, "docker-compose.yml"), "w") as dc:
                df.write(result["docker_compose"])

        elif deployment_type == "k8s":
            k8s_dir = os.path.join(export_dir, "k8s")
            os.makedirs(k8s_dir, exist_ok=True)
            k8s_files = PYTHON_K8S_TEMPLATE if project_type == "python" else REACT_K8S_TEMPLATE
            for filename, content in k8s_files.items():
                with open(os.path.join(k8s_dir, filename), "w") as f:
                    f.write(content)

        zip_path = os.path.join(temp_dir, "export_package.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(export_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, export_dir)
                    zipf.write(full_path, arcname=arcname)

        return FileResponse(zip_path, media_type="application/zip", filename="export_package.zip")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {e}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.get("/")
async def health_check():
    return {"status": "healthy"}

# Utility functions

async def extract_zip(upload_file, extract_to):
    # Ensure the file is at the beginning
    await upload_file.seek(0)
    # Create a temporary file to handle the upload
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        # Copy the contents of the uploaded file to the temporary file
        shutil.copyfileobj(upload_file.file, temp_file)
        temp_file.flush()
        # Now use the temporary file to extract the zip
        with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
    # Clean up the temporary file
    os.unlink(temp_file.name)

def find_project_root(base_dir):
    for root, dirs, files in os.walk(base_dir):
        if 'requirements.txt' in files or 'package.json' in files:
            return root
    return base_dir

def detect_project_type(path):
    if os.path.exists(os.path.join(path, 'requirements.txt')):
        return "python"
    elif os.path.exists(os.path.join(path, 'package.json')):
        return "react"
    else:
        raise Exception("Unsupported project type")

def detect_react_framework(path):
    package_json_path = os.path.join(path, 'package.json')
    
    with open(package_json_path, 'r') as f:
        package_data = json.load(f)
    
    dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
    
    # Detect build command from scripts
    build_cmd = "npm run build"
    if 'scripts' in package_data and 'build' in package_data['scripts']:
        build_cmd = package_data['scripts']['build']
    
    # Check for Next.js
    if 'next' in dependencies:
        output_dir = 'out' if 'export' in package_data.get('scripts', {}) else '.next'
        return "next", output_dir, build_cmd
    
    # Check for Gatsby
    elif 'gatsby' in dependencies:
        return "gatsby", "public", build_cmd
    
    # Default to regular React (Create React App)
    else:
        return "react", "build", build_cmd

def generate_python_dockerfile(project_path):
    entry_point = "main.py" if os.path.exists(os.path.join(project_path, "main.py")) else "app.py"
    install_cmds = "RUN pip install -r requirements.txt" if os.path.exists(os.path.join(project_path, "requirements.txt")) else ""
    
    return {
        "dockerfile": PYTHON_DOCKERFILE_TEMPLATE.format(install_commands=install_cmds, entry_point=entry_point),
        "docker_compose": PYTHON_DOCKER_COMPOSE_TEMPLATE.format(entry_point=entry_point),
        "entry_point": entry_point,
        "build_command": "docker build -t pythonapp .",
        "run_command": "docker run -p 5000:5000 pythonapp",
        "docker_compose_command": "docker-compose up"
    }

def generate_react_dockerfile(path):
    framework, output_dir, build_cmd = detect_react_framework(path)
    build_command = "RUN npm run build && npm run export" if framework == "next" else f"RUN {build_cmd}"
    
    return {
        "dockerfile": REACT_DOCKERFILE_TEMPLATE.format(build_command=build_command, build_output=output_dir),
        "docker_compose": REACT_DOCKER_COMPOSE_TEMPLATE,
        "framework": framework,
        "build_output": output_dir,
        "build_command": "docker build -t reactapp .",
        "run_command": "docker run -p 80:80 reactapp",
        "docker_compose_command": "docker-compose up"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
