# Docker guide

This guide explains how to run Rosettier v2 with Docker.

## Requirements

- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- Docker daemon running locally

Check Docker availability:

```bash
docker --version
```

## Build image

From the repository root:

```bash
docker build -t rosettier-v2 .
```

## Run app

```bash
docker run --rm -p 8501:8501 rosettier-v2
```

Then open: <http://localhost:8501>

## Stop the app

- Press `Ctrl+C` in the terminal where the container is running.
- The container is removed automatically because `--rm` is used.

## Mount local files

To share local files with the container:

```bash
docker run --rm -p 8501:8501 -v "$(pwd):/work" rosettier-v2
```

PowerShell note: if `$(pwd)` does not work, use `${PWD}`.

## Common Docker issues

### Port already allocated

If you see a port-binding error, use a different local port:

```bash
docker run --rm -p 8502:8501 rosettier-v2
```

Open <http://localhost:8502>.

### Docker not running

If Docker commands fail to connect to the daemon, start Docker Desktop/Engine and retry.
