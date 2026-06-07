#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import posixpath
import shlex
import sys
import tarfile
from datetime import datetime
from pathlib import Path, PurePosixPath

import paramiko


DEFAULT_CMAKE_OPTIONS = [
    "-DCLIENT=OFF",
    "-DTOOLS=OFF",
    "-DDOWNLOAD_GTEST=OFF",
    "-DVIDEORECORDER=OFF",
    "-DVULKAN=OFF",
    "-DAUTOUPDATE=OFF",
    "-DPREFER_BUNDLED_LIBS=ON",
]

EXCLUDED_DIR_NAMES = {
    ".git",
    ".idea",
    ".vs",
    ".vscode",
    "__pycache__",
    "target",
}

EXCLUDED_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tar",
    ".tar.gz",
    ".zip",
}


class DeployError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload DDNet source to Ubuntu, build game-server, and optionally install it."
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("ddnet_deploy.config.json")),
        help="Path to the deployment config JSON file.",
    )
    parser.add_argument(
        "--password",
        help="SSH password. If omitted, DDNET_DEPLOY_PASSWORD is used, then an interactive prompt.",
    )
    parser.add_argument(
        "--install-runtime",
        action="store_true",
        help="Copy the built DDNet-Server into the runtime directory after a successful build.",
    )
    parser.add_argument(
        "--restart-service",
        action="store_true",
        help="Restart the systemd service after installing the runtime binary.",
    )
    parser.add_argument(
        "--skip-local-build-check",
        action="store_true",
        help="Skip checking the local Windows server binary before deployment.",
    )
    parser.add_argument(
        "--build-jobs",
        type=int,
        default=2,
        help="Parallel jobs for the remote CMake build. Default: 2.",
    )
    return parser.parse_args()


def load_config(config_path: Path) -> dict:
    if not config_path.is_file():
        raise DeployError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    required = [
        "local_source_dir",
        "local_windows_server_binary",
        "remote_host",
        "remote_port",
        "remote_user",
        "remote_source_dir",
        "remote_build_dir",
        "remote_runtime_dir",
        "remote_deploy_root",
        "service_name",
    ]
    missing = [key for key in required if key not in config]
    if missing:
        raise DeployError(f"Config file is missing required keys: {', '.join(missing)}")

    config.setdefault("cmake_options", list(DEFAULT_CMAKE_OPTIONS))
    config.setdefault(
        "local_artifacts_dir",
        str(Path(config["local_source_dir"]).resolve().parent / "deploy-artifacts"),
    )
    return config


def log(message: str) -> None:
    print(f"[ddnet-deploy] {message}")


def ensure_local_state(config: dict, skip_local_build_check: bool) -> tuple[Path, Path, Path]:
    source_dir = Path(config["local_source_dir"]).resolve()
    artifacts_dir = Path(config["local_artifacts_dir"]).resolve()
    local_binary = Path(config["local_windows_server_binary"]).resolve()

    if not source_dir.is_dir():
        raise DeployError(f"Local source directory not found: {source_dir}")
    if not (source_dir / "CMakeLists.txt").is_file():
        raise DeployError(f"Missing CMakeLists.txt in source directory: {source_dir}")
    if not (source_dir / "Cargo.toml").is_file():
        raise DeployError(f"Missing Cargo.toml in source directory: {source_dir}")

    if not skip_local_build_check and not local_binary.is_file():
        raise DeployError(
            "Local Windows server binary was not found. "
            f"Expected: {local_binary}. "
            "Build locally first, or rerun with --skip-local-build-check."
        )

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return source_dir, artifacts_dir, local_binary


def should_exclude(rel_path: Path) -> bool:
    parts = rel_path.parts
    if any(part in EXCLUDED_DIR_NAMES for part in parts):
        return True
    name = rel_path.name
    return any(name.endswith(suffix) for suffix in EXCLUDED_FILE_SUFFIXES)


def create_archive(source_dir: Path, artifacts_dir: Path) -> tuple[Path, str, int]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = artifacts_dir / f"ddnet-src-{timestamp}.tar.gz"
    file_count = 0

    with tarfile.open(archive_path, "w:gz") as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            rel_path = path.relative_to(source_dir)
            if should_exclude(rel_path):
                continue
            archive.add(path, arcname=rel_path.as_posix(), recursive=False)
            file_count += 1

    sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    return archive_path, sha256, file_count


def resolve_password(args: argparse.Namespace) -> str:
    password = args.password or os.environ.get("DDNET_DEPLOY_PASSWORD")
    if password:
        return password
    return getpass.getpass("SSH password: ")


def connect_ssh(config: dict, password: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=config["remote_host"],
        port=int(config["remote_port"]),
        username=config["remote_user"],
        password=password,
        timeout=20,
        allow_agent=False,
        look_for_keys=False,
    )
    return client


def sftp_mkdir_p(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    remote_dir = str(PurePosixPath(remote_dir))
    current = PurePosixPath("/")
    for part in PurePosixPath(remote_dir).parts[1:]:
        current = current / part
        try:
            sftp.stat(str(current))
        except FileNotFoundError:
            sftp.mkdir(str(current))


def upload_archive(
    ssh: paramiko.SSHClient,
    config: dict,
    archive_path: Path,
    sha256: str,
) -> tuple[str, str]:
    remote_deploy_root = str(PurePosixPath(config["remote_deploy_root"]))
    remote_incoming_dir = posixpath.join(remote_deploy_root, "incoming")
    remote_archive = posixpath.join(remote_incoming_dir, archive_path.name)
    remote_sha_file = f"{remote_archive}.sha256"

    with ssh.open_sftp() as sftp:
        sftp_mkdir_p(sftp, remote_incoming_dir)
        sftp.put(str(archive_path), remote_archive)
        with sftp.file(remote_sha_file, "w") as handle:
            handle.write(f"{sha256}  {archive_path.name}\n")

    return remote_archive, remote_sha_file


def run_remote_deploy(
    ssh: paramiko.SSHClient,
    config: dict,
    archive_name: str,
    archive_sha256: str,
    sudo_password: str,
    build_jobs: int,
    install_runtime: bool,
    restart_service: bool,
) -> None:
    remote_deploy_root = str(PurePosixPath(config["remote_deploy_root"]))
    incoming_archive = posixpath.join(remote_deploy_root, "incoming", archive_name)
    incoming_sha_file = f"{incoming_archive}.sha256"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    cmake_options = config.get("cmake_options", DEFAULT_CMAKE_OPTIONS)
    cmake_args = " ".join(shlex.quote(option) for option in cmake_options)

    script = f"""#!/usr/bin/env bash
set -euo pipefail

TIMESTAMP={shlex.quote(timestamp)}
REMOTE_SOURCE_DIR={shlex.quote(config["remote_source_dir"])}
REMOTE_BUILD_DIR={shlex.quote(config["remote_build_dir"])}
REMOTE_RUNTIME_DIR={shlex.quote(config["remote_runtime_dir"])}
REMOTE_DEPLOY_ROOT={shlex.quote(remote_deploy_root)}
INCOMING_ARCHIVE={shlex.quote(incoming_archive)}
INCOMING_SHA_FILE={shlex.quote(incoming_sha_file)}
EXPECTED_SHA={shlex.quote(archive_sha256)}
SUDO_PASSWORD={shlex.quote(sudo_password)}
SERVICE_NAME={shlex.quote(config["service_name"])}
BUILD_JOBS={int(build_jobs)}
INSTALL_RUNTIME={"1" if install_runtime else "0"}
RESTART_SERVICE={"1" if restart_service else "0"}

STAGING_ROOT="$REMOTE_DEPLOY_ROOT/staging/$TIMESTAMP"
TMP_SOURCE_DIR="$REMOTE_DEPLOY_ROOT/tmp/ddnet-src-$TIMESTAMP"
BACKUP_ROOT="$REMOTE_DEPLOY_ROOT/backups"
SOURCE_BACKUP_DIR="$BACKUP_ROOT/ddnet-src-$TIMESTAMP"
RUNTIME_BACKUP_FILE="$BACKUP_ROOT/DDNet-Server-$TIMESTAMP"
RUNTIME_BINARY="$REMOTE_RUNTIME_DIR/DDNet-Server"
BUILT_BINARY="$REMOTE_BUILD_DIR/DDNet-Server"

mkdir -p "$REMOTE_DEPLOY_ROOT/incoming" "$REMOTE_DEPLOY_ROOT/staging" "$REMOTE_DEPLOY_ROOT/tmp" "$BACKUP_ROOT"

if [ ! -f "$INCOMING_ARCHIVE" ]; then
    echo "Remote archive is missing: $INCOMING_ARCHIVE" >&2
    exit 1
fi

echo "$EXPECTED_SHA  $INCOMING_ARCHIVE" | sha256sum -c -

rm -rf "$STAGING_ROOT" "$TMP_SOURCE_DIR"
mkdir -p "$STAGING_ROOT/src"
tar -xzf "$INCOMING_ARCHIVE" -C "$STAGING_ROOT/src"

test -f "$STAGING_ROOT/src/CMakeLists.txt"
test -f "$STAGING_ROOT/src/Cargo.toml"

mv "$STAGING_ROOT/src" "$TMP_SOURCE_DIR"
rm -rf "$STAGING_ROOT"

rm -rf "$REMOTE_BUILD_DIR"
cmake -S "$TMP_SOURCE_DIR" -B "$REMOTE_BUILD_DIR" {cmake_args}
cmake --build "$REMOTE_BUILD_DIR" -j"$BUILD_JOBS" --target game-server

test -f "$BUILT_BINARY"

if [ -d "$REMOTE_SOURCE_DIR" ]; then
    rm -rf "$SOURCE_BACKUP_DIR"
    mv "$REMOTE_SOURCE_DIR" "$SOURCE_BACKUP_DIR"
fi
mv "$TMP_SOURCE_DIR" "$REMOTE_SOURCE_DIR"

if [ "$INSTALL_RUNTIME" = "1" ]; then
    if [ -f "$RUNTIME_BINARY" ]; then
        cp -a "$RUNTIME_BINARY" "$RUNTIME_BACKUP_FILE"
    fi
    install -m 755 "$BUILT_BINARY" "$RUNTIME_BINARY"
    if [ "$RESTART_SERVICE" = "1" ]; then
        printf '%s\n' "$SUDO_PASSWORD" | sudo -S -p '' systemctl restart "$SERVICE_NAME"
        printf '%s\n' "$SUDO_PASSWORD" | sudo -S -p '' systemctl is-active "$SERVICE_NAME"
    fi
fi

echo "SOURCE_READY=$REMOTE_SOURCE_DIR"
echo "BUILD_READY=$BUILT_BINARY"
if [ "$INSTALL_RUNTIME" = "1" ]; then
    echo "RUNTIME_READY=$RUNTIME_BINARY"
fi
if [ "$RESTART_SERVICE" = "1" ]; then
    echo "SERVICE_READY=$SERVICE_NAME"
fi
"""

    command = "bash -s"
    stdin, stdout, stderr = ssh.exec_command(command, timeout=7200)
    stdin.write(script)
    stdin.flush()
    stdin.channel.shutdown_write()

    stdout_text = stdout.read().decode("utf-8", errors="replace")
    stderr_text = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()

    if stdout_text.strip():
        print(stdout_text.rstrip())
    if stderr_text.strip():
        print(stderr_text.rstrip(), file=sys.stderr)

    if exit_code != 0:
        raise DeployError(f"Remote deployment failed with exit code {exit_code}.")


def main() -> int:
    args = parse_args()
    if args.restart_service and not args.install_runtime:
        raise DeployError("--restart-service requires --install-runtime.")
    if args.build_jobs < 1:
        raise DeployError("--build-jobs must be at least 1.")

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    source_dir, artifacts_dir, local_binary = ensure_local_state(
        config, skip_local_build_check=args.skip_local_build_check
    )

    if not args.skip_local_build_check:
        log(f"Local Windows build check passed: {local_binary}")
    log(f"Packing source from: {source_dir}")
    archive_path, sha256, file_count = create_archive(source_dir, artifacts_dir)
    log(f"Archive ready: {archive_path}")
    log(f"Archive SHA256: {sha256}")
    log(f"Archived files: {file_count}")

    password = resolve_password(args)
    ssh = None
    try:
        log(f"Connecting to {config['remote_user']}@{config['remote_host']}:{config['remote_port']}")
        ssh = connect_ssh(config, password)
        remote_archive, _ = upload_archive(ssh, config, archive_path, sha256)
        log(f"Uploaded archive to: {remote_archive}")
        run_remote_deploy(
            ssh=ssh,
            config=config,
            archive_name=archive_path.name,
            archive_sha256=sha256,
            sudo_password=password,
            build_jobs=args.build_jobs,
            install_runtime=args.install_runtime,
            restart_service=args.restart_service,
        )
        if args.install_runtime:
            if args.restart_service:
                log("Remote build, install, and service restart all completed successfully.")
            else:
                log("Remote build and install completed successfully.")
        else:
            log("Remote build completed successfully. Runtime binary was not replaced.")
            log(
                "If you want to install it next time, rerun with --install-runtime "
                "and optionally --restart-service."
            )
    finally:
        if ssh is not None:
            ssh.close()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DeployError as exc:
        print(f"[ddnet-deploy] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
