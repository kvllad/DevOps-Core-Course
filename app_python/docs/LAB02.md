# Lab 2 — Docker Containerization (Python)

## Docker Best Practices Applied
- **Pinned base image**: `python:3.13-slim` for predictable builds and fewer surprise changes.
- **Non-root runtime user**: create `app` user and switch to it to reduce blast radius if the app is compromised.
- **Layer caching**: copy `requirements.txt` first, install deps, then copy `app.py` so dependency layers are reused across code changes.
- **Minimal context**: `.dockerignore` excludes tests, docs, venvs, and VCS files to reduce build context size and speed up builds.
- **No cache pip installs**: `--no-cache-dir` keeps the image smaller by not persisting wheels.
- **Only necessary files copied**: `app.py` and `requirements.txt` only.

**Dockerfile snippets**
```dockerfile
FROM python:3.13-slim

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home --home /home/app app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app app.py ./

USER app
```

**Why this matters**
- Pinned image + cache-friendly ordering makes builds faster and more reproducible.
- Non-root user prevents accidental writes to system paths and reduces privilege escalation risk.
- `.dockerignore` prevents unnecessary files from bloating the image or leaking local artifacts.

## Image Information & Decisions
- **Base image**: `python:3.13-slim`.
  - Rationale: Official image, current Python, smaller footprint than full image while staying Debian-based (good compatibility vs Alpine).
- **Final image size** (from `docker image ls`):
```
IMAGE                          ID             DISK USAGE   CONTENT SIZE   EXTRA
devops-info-service-py:lab02   644c0238f314        254MB         54.7MB
```
- **Layer structure** (top-down): base -> env -> workdir -> create user -> copy deps -> install deps -> copy app -> switch user -> expose -> cmd.
- **Optimizations**: `--no-cache-dir`, `.dockerignore`, minimal file copy.

## Build & Run Process
**Build output**
```
DEPRECATED: The legacy builder is deprecated and will be removed in a future release.
            Install the buildx component to build images with BuildKit:
            https://docs.docker.com/go/buildx/

Sending build context to Docker daemon  10.75kB
Step 1/10 : FROM python:3.13-slim
3.13-slim: Pulling from library/python
14c37da83ac4: Pulling fs layer
4c4a8dac9336: Pulling fs layer
af94c6242df3: Pulling fs layer
3ea009573b47: Pulling fs layer
4c4a8dac9336: Download complete
3ea009573b47: Download complete
14c37da83ac4: Download complete
af94c6242df3: Download complete
3ea009573b47: Pull complete
14c37da83ac4: Pull complete
af94c6242df3: Pull complete
4c4a8dac9336: Pull complete
Digest: sha256:3de9a8d7aedbb7984dc18f2dff178a7850f16c1ae7c34ba9d7ecc23d0755e35f
Status: Downloaded newer image for python:3.13-slim
 ---> 3de9a8d7aedb
Step 2/10 : ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1
 ---> Running in ee84262de00d
 ---> Removed intermediate container ee84262de00d
 ---> ea43fbbe8148
Step 3/10 : WORKDIR /app
 ---> Running in 15ccbbd207ae
 ---> Removed intermediate container 15ccbbd207ae
 ---> a24581fa07e9
Step 4/10 : RUN groupadd --system app && useradd --system --gid app --create-home --home /home/app app
 ---> Running in 9edd3ca62efe
 ---> Removed intermediate container 9edd3ca62efe
 ---> 557ab44e51ca
Step 5/10 : COPY requirements.txt ./
 ---> db29880eca6c
Step 6/10 : RUN pip install --no-cache-dir -r requirements.txt
 ---> Running in edf56705d48b
Collecting fastapi==0.115.0 (from -r requirements.txt (line 1))
  Downloading fastapi-0.115.0-py3-none-any.whl.metadata (27 kB)
Collecting uvicorn==0.32.0 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
  Downloading uvicorn-0.32.0-py3-none-any.whl.metadata (6.6 kB)
Collecting starlette<0.39.0,>=0.37.2 (from fastapi==0.115.0->-r requirements.txt (line 1))
  Downloading starlette-0.38.6-py3-none-any.whl.metadata (6.0 kB)
Collecting pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4 (from fastapi==0.115.0->-r requirements.txt (line 1))
  Downloading pydantic-2.12.5-py3-none-any.whl.metadata (90 kB)
Collecting typing-extensions>=4.8.0 (from fastapi==0.115.0->-r requirements.txt (line 1))
  Downloading typing_extensions-4.15.0-py3-none-any.whl.metadata (3.3 kB)
Collecting click>=7.0 (from uvicorn==0.32.0->uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
  Downloading click-8.3.1-py3-none-any.whl.metadata (2.6 kB)
Collecting h11>=0.8 (from uvicorn==0.32.0->uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
  Downloading h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
Collecting httptools>=0.5.0 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
  Downloading httptools-0.7.1-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (3.5 kB)
Collecting python-dotenv>=0.13 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
  Downloading python_dotenv-1.2.1-py3-none-any.whl.metadata (25 kB)
Collecting pyyaml>=5.1 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
  Downloading pyyaml-6.0.3-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (2.4 kB)
Collecting uvloop!=0.15.0,!=0.15.1,>=0.14.0 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
  Downloading uvloop-0.22.1-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (4.9 kB)
Collecting watchfiles>=0.13 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
  Downloading watchfiles-1.1.1-cp313-cp313-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.9 kB)
Collecting websockets>=10.4 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
  Downloading websockets-16.0-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (6.8 kB)
Collecting annotated-types>=0.6.0 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.115.0->-r requirements.txt (line 1))
  Downloading annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
Collecting pydantic-core==2.41.5 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.115.0->-r requirements.txt (line 1))
  Downloading pydantic_core-2.41.5-cp313-cp313-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (7.3 kB)
Collecting typing-inspection>=0.4.2 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.115.0->-r requirements.txt (line 1))
  Downloading typing_inspection-0.4.2-py3-none-any.whl.metadata (2.6 kB)
Collecting anyio<5,>=3.4.0 (from starlette<0.39.0,>=0.37.2->fastapi==0.115.0->-r requirements.txt (line 1))
  Downloading anyio-4.12.1-py3-none-any.whl.metadata (4.3 kB)
Collecting idna>=2.8 (from anyio<5,>=3.4.0->starlette<0.39.0,>=0.37.2->fastapi==0.115.0->-r requirements.txt (line 1))
  Downloading idna-3.11-py3-none-any.whl.metadata (8.4 kB)
Downloading fastapi-0.115.0-py3-none-any.whl (94 kB)
Downloading uvicorn-0.32.0-py3-none-any.whl (63 kB)
Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
Downloading pydantic_core-2.41.5-cp313-cp313-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.9/1.9 MB 1.7 MB/s  0:00:01
Downloading starlette-0.38.6-py3-none-any.whl (71 kB)
Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
Downloading click-8.3.1-py3-none-any.whl (108 kB)
Downloading h11-0.16.0-py3-none-any.whl (37 kB)
Downloading httptools-0.7.1-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (473 kB)
Downloading idna-3.11-py3-none-any.whl (71 kB)
Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
Downloading pyyaml-6.0.3-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (767 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 767.1/767.1 kB 2.4 MB/s  0:00:00
Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
Downloading uvloop-0.22.1-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (4.3 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.3/4.3 MB 2.0 MB/s  0:00:02
Downloading watchfiles-1.1.1-cp313-cp313-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (449 kB)
Downloading websockets-16.0-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (186 kB)
Installing collected packages: websockets, uvloop, typing-extensions, pyyaml, python-dotenv, idna, httptools, h11, click, annotated-types, uvicorn, typing-inspection, pydantic-core, anyio, watchfiles, starlette, pydantic, fastapi

Successfully installed annotated-types-0.7.0 anyio-4.12.1 click-8.3.1 fastapi-0.115.0 h11-0.16.0 httptools-0.7.1 idna-3.11 pydantic-2.12.5 pydantic-core-2.41.5 python-dotenv-1.2.1 pyyaml-6.0.3 starlette-0.38.6 typing-extensions-4.15.0 typing-inspection-0.4.2 uvicorn-0.32.0 uvloop-0.22.1 watchfiles-1.1.1 websockets-16.0
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.

[notice] A new release of pip is available: 25.3 -> 26.0.1
[notice] To update, run: pip install --upgrade pip
 ---> Removed intermediate container edf56705d48b
 ---> 0c224bb4e095
Step 7/10 : COPY --chown=app:app app.py ./
 ---> 1cf82ed75eb3
Step 8/10 : USER app
 ---> Running in cd534cb52033
 ---> Removed intermediate container cd534cb52033
 ---> 05fd9def45e5
Step 9/10 : EXPOSE 5000
 ---> Running in 96aff6201b4c
 ---> Removed intermediate container 96aff6201b4c
 ---> f5f4588a3fc2
Step 10/10 : CMD ["python", "app.py"]
 ---> Running in ed99ff19509f
 ---> Removed intermediate container ed99ff19509f
 ---> 644c0238f314
Successfully built 644c0238f314
Successfully tagged devops-info-service-py:lab02
```

**Run output**
```
$ docker run -d --name devops-info-py -p 5000:5000 devops-info-service-py:lab02
b076c4b1ddb6e1809a97cf1d70814d37f7208a8882deafec2c12b91c11d8d943

$ docker ps --filter name=devops-info-py
CONTAINER ID   IMAGE                          COMMAND           CREATED         STATUS         PORTS                                         NAMES
b076c4b1ddb6   devops-info-service-py:lab02   "python app.py"   6 seconds ago   Up 7 seconds   0.0.0.0:5000->5000/tcp, [::]:5000->5000/tcp   devops-info-py
```

**Endpoint tests (inside container)**
```
$ docker exec devops-info-py python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/health').read().decode())"
{"status":"healthy","timestamp":"2026-02-08T11:19:43.481510Z","uptime_seconds":44}

$ docker exec devops-info-py python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/').read().decode()[:350])"
{"service":{"name":"devops-info-service","version":"1.0.0","description":"DevOps course info service","framework":"FastAPI"},"system":{"hostname":"b076c4b1ddb6","platform":"Linux","platform_version":"Linux-6.8.0-64-generic-aarch64-with-glibc2.41","architecture":"aarch64","cpu_count":2,"python_version":"3.13.12"},"runtime":{"uptime_seconds":51,"upti
```

**Tagging strategy**
- `vladk6813050/devops-info-service-py:lab02` to indicate the lab version explicitly and avoid ambiguity with `latest`.

**Docker Hub push output**
```
The push refers to repository [docker.io/vladk6813050/devops-info-service-py]
4c4a8dac9336: Mounted from library/python
af94c6242df3: Mounted from library/python
3ea009573b47: Mounted from library/python
14c37da83ac4: Mounted from library/python
ae98e36f2fdf: Pushed
87b8a1390787: Pushed
b0ce68166738: Pushed
ed7ad880dcd5: Pushed
219ca8734591: Pushed
lab02: digest: sha256:644c0238f314a3d85bed5962e6d302bc83aab91f158902616e7c1859c54a8bd8 size: 2271
```

**Docker Hub pull verification**
```
lab02: Pulling from vladk6813050/devops-info-service-py
Digest: sha256:644c0238f314a3d85bed5962e6d302bc83aab91f158902616e7c1859c54a8bd8
Status: Image is up to date for vladk6813050/devops-info-service-py:lab02
docker.io/vladk6813050/devops-info-service-py:lab02
```

**Docker Hub repository URL**
- `https://hub.docker.com/r/vladk6813050/devops-info-service-py`

## Technical Analysis
- **Why this Dockerfile works**: dependencies are installed before app code, the app runs as a non-root user, and `CMD` launches `app.py` on the container’s exposed port.
- **What if layer order changes**: copying app before `requirements.txt` would invalidate the pip layer on every code change, slowing rebuilds.
- **Security considerations**: non-root user, reduced base image, and no extra tools installed.
- **.dockerignore impact**: reduces build context size, prevents accidental inclusion of dev artifacts, speeds up builds.

## Challenges & Solutions
- **Host curl could not reach container ports in this environment**: port-forwarding from Docker wasn’t accessible from the sandbox. I verified endpoints by executing HTTP requests inside the running container via `docker exec`.
- **Pip root warning during build**: expected for image build layers; runtime is non-root.
