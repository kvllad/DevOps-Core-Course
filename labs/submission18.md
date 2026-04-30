# Lab 18 — Reproducible Builds with Nix

Execution date: 2026-05-01

Verification environment:
- Host: macOS on Apple Silicon
- Nix verification: `nixos/nix:2.24.14` container
- Docker verification: Docker 29.4.0 on host

Reason for containerized verification:
- `nix` is not installed on the host machine.
- The lab was therefore verified inside a clean Linux container with the repository mounted into `/workspace`.
- This still produced real Nix store paths, real Docker image hashes, and working runtime checks.

## Files Delivered

- `labs/lab18/app_python/app.py`
- `labs/lab18/app_python/requirements.txt`
- `labs/lab18/app_python/Dockerfile`
- `labs/lab18/app_python/default.nix`
- `labs/lab18/app_python/docker.nix`
- `labs/lab18/app_python/flake.nix`
- `labs/lab18/app_python/flake.lock`
- `labs/lab18/evidence/*`

## Task 1 — Reproducible Python App

### Traditional Lab 1 workflow

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Why this is weaker than Nix:
- it depends on the host Python version
- it resolves dependencies at install time
- transitive dependencies are not fully pinned
- it does not produce content-addressed outputs

### `default.nix`

Implementation summary:
- uses `pkgs.python3.withPackages` to build a fixed Python environment
- wraps `app.py` as `devops-info-service`
- installs only the application payload and launch wrapper

Key fields:
- `pname` / `version`: package identity
- `src = pkgs.lib.cleanSource ./.;`: clean local source tree
- `nativeBuildInputs = [ pkgs.makeWrapper ];`: wrapper support
- `makeWrapper ... --add-flags "$out/app/app.py"`: executable entrypoint

### Verification commands

```bash
cd labs/lab18/app_python
nix-build default.nix
readlink result
./result/bin/devops-info-service
rm result
nix-store --delete <store-path>
nix-build default.nix
readlink result
```

### Reproducibility proof

- First store path:
  `/nix/store/v1k46wwl0lz6v8yjxdrccaji9gvajr72-devops-info-service-1.0.0`
- Second store path:
  `/nix/store/v1k46wwl0lz6v8yjxdrccaji9gvajr72-devops-info-service-1.0.0`
- Conclusion:
  identical output path after deleting the previous result and rebuilding

Runtime verification:

```json
{"status":"healthy","timestamp":"2026-04-30T22:26:44.366888Z","uptime_seconds":93}
```

Evidence:
- `labs/lab18/evidence/app-store-path-1.txt`
- `labs/lab18/evidence/app-store-path-2.txt`
- `labs/lab18/evidence/nix-app-health.json`
- `labs/lab18/evidence/nix-app-run.log`
- `labs/lab18/evidence/nix-version.txt`

### `pip` vs Nix comparison

| Aspect | Lab 1 (`pip` + `venv`) | Lab 18 (`nix-build`) |
|---|---|---|
| Python version | Host-dependent | Fixed by selected `nixpkgs` |
| Direct dependencies | Pinned partially | Fixed in Nix package set |
| Transitive dependencies | Can drift | Part of full closure |
| Output path | None | Content-addressed |
| Rebuild result | Approximate | Identical store path |

### Store path format

Example:

```text
/nix/store/v1k46wwl0lz6v8yjxdrccaji9gvajr72-devops-info-service-1.0.0
```

Meaning:
- `/nix/store`: Nix content store
- `v1k46wwl0lz6v8yjxdrccaji9gvajr72`: hash of build inputs
- `devops-info-service-1.0.0`: human-readable package name/version

Reflection:
- If Nix had been used in Lab 1 from the start, the app environment would have been reproducible by definition instead of “repeatable if the host still looks the same.”

## Task 2 — Reproducible Docker Images

### Traditional Lab 2 Dockerfile

Source:
- `labs/lab18/app_python/Dockerfile`

Traditional image verification:

```bash
docker build --no-cache -t lab2-app:test1 ./app_python
docker save lab2-app:test1 | shasum -a 256

docker build --no-cache -t lab2-app:test2 ./app_python
docker save lab2-app:test2 | shasum -a 256
```

Results:
- Build 1 tar hash:
  `08a0b29d625d5946be39fd778c371da9d433694985a333348fb4cd58b879df3b`
- Build 2 tar hash:
  `532e064c7b887972f55ace6899255a90b879418d9f4229d0793adb82d2c0b79c`
- Build 1 created timestamp:
  `2026-05-01T01:31:30.436141061+03:00`
- Build 2 created timestamp:
  `2026-05-01T01:32:00.212278643+03:00`

### `docker.nix`

Implementation summary:
- imports the application derivation from `default.nix`
- builds the image with `pkgs.dockerTools.buildLayeredImage`
- uses deterministic timestamp `1970-01-01T00:00:01Z`
- sets `Cmd`, `Env`, exposed port, and `/data` volume

### Nix image verification

```bash
cd labs/lab18/app_python
nix-build docker.nix
sha256sum result
rm result
nix-store --delete <image-store-path>
nix-build docker.nix
sha256sum result
```

Results:
- Nix image hash build 1:
  `3150677f70829bf44b26ff4661af90102f067711f9a38d187e82cd1fe4665925`
- Nix image hash build 2:
  `3150677f70829bf44b26ff4661af90102f067711f9a38d187e82cd1fe4665925`
- Nix image created timestamp:
  `1970-01-01T00:00:01Z`

### Runtime verification

Both images were loaded and run side-by-side:

```json
traditional_health:
{"status":"healthy","timestamp":"2026-04-30T22:32:14.077842Z","uptime_seconds":4}

nix_health:
{"status":"healthy","timestamp":"2026-04-30T22:32:14.113561Z","uptime_seconds":4}
```

### Comparison table

| Metric | Lab 2 Dockerfile | Lab 18 Nix dockerTools |
|---|---|---|
| Tarball hash build 1 | `08a0b29d625d5946be39fd778c371da9d433694985a333348fb4cd58b879df3b` | `3150677f70829bf44b26ff4661af90102f067711f9a38d187e82cd1fe4665925` |
| Tarball hash build 2 | `532e064c7b887972f55ace6899255a90b879418d9f4229d0793adb82d2c0b79c` | `3150677f70829bf44b26ff4661af90102f067711f9a38d187e82cd1fe4665925` |
| Reproducible | No | Yes |
| Created timestamp | Changes per build | Fixed |
| Image size | `269MB` | `430MB` |

Important observation:
- The Nix image was reproducible, but not smaller in this particular implementation.
- The deterministic property is proven; image size still depends on the chosen closure contents.

Why the traditional Dockerfile is not bit-for-bit reproducible:
- image metadata changes across builds
- base image contents can change over time
- package installation happens at build time
- saved image tarballs include build-specific metadata

Reflection:
- If Lab 2 were redone with Nix, I would keep the container interface but build the image from a pinned derivation rather than from a mutable base image tag.

Evidence:
- `labs/lab18/evidence/traditional-image-1.sha256`
- `labs/lab18/evidence/traditional-image-2.sha256`
- `labs/lab18/evidence/nix-image-build-1.sha256`
- `labs/lab18/evidence/nix-image-build-2.sha256`
- `labs/lab18/evidence/docker-compare.txt`
- `labs/lab18/evidence/docker-runtime-check.txt`

## Bonus — Nix Flakes

### `flake.nix`

The flake was finalized to support pure evaluation on multiple systems:
- `aarch64-darwin`
- `aarch64-linux`
- `x86_64-darwin`
- `x86_64-linux`

This was required because `builtins.currentSystem` fails under pure flake evaluation.

### Locked dependency proof

Locked `nixpkgs` entry from `flake.lock`:

```json
{
  "lastModified": 1751274312,
  "narHash": "sha256-/bVBlRpECLVzjV19t5KMdMFWSwKLtb5RyXdjz3LJT+g=",
  "owner": "NixOS",
  "repo": "nixpkgs",
  "rev": "50ab793786d9de88ee30ec4e4c24fb4236fc2674",
  "type": "github"
}
```

### Flake verification

Commands:

```bash
nix build
nix build .#dockerImage
nix develop -c python --version
```

Results:
- Default flake build output:
  `/nix/store/hw7a93ffkxdpyagnzfj8s9jkx8rkz13h-devops-info-service-1.0.0`
- Flake Docker image output:
  `/nix/store/im1pynkj065rvbsw0pdhx81djh8ysk9q-devops-info-service-nix.tar.gz`
- `nix develop` Python version:
  `Python 3.12.8`

Note:
- The standalone `default.nix` build used the container image’s ambient `<nixpkgs>` channel.
- The flake build used the pinned `nixos-24.11` input from `flake.lock`.
- The flake path is therefore the stronger reproducibility mechanism in this lab.

### Helm vs Flakes

| Aspect | Lab 10 Helm values | Lab 18 Nix Flakes |
|---|---|---|
| Locks image tag | Yes | Indirectly through derivation outputs |
| Locks Python dependencies | No | Yes |
| Locks build toolchain | No | Yes |
| Cross-machine consistency | Depends on image contents | Pinned by lock file |
| Time-stable reproducibility | Limited | Strong |

Reflection:
- Helm pins deployment inputs.
- Flakes pin build inputs.
- Used together, Helm handles release orchestration while Nix handles artifact reproducibility.

Evidence:
- `labs/lab18/evidence/flake-default-path.txt`
- `labs/lab18/evidence/flake-docker-path.txt`
- `labs/lab18/evidence/nix-develop-python.txt`

## Final Summary

Completed:
- reproducible Nix application build
- reproducible Nix Docker image build
- direct comparison against traditional Docker builds
- flake-based pinned build workflow
- runtime verification for both traditional and Nix images

Verified outcomes:
- app rebuild path stayed identical
- Nix image SHA256 stayed identical
- traditional Docker image SHA256 changed between builds
- both containers returned healthy responses
- `nix build`, `nix build .#dockerImage`, and `nix develop` succeeded after fixing `flake.nix`
