"""
FastAPI application and local REST / UDS API server for WhitelistBypass Core.
"""

import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
import pwd
import grp
import shutil
from typing import Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from core import __version__
from core.commands import COMMAND_REGISTRY, resolve_command
from core.config import CoreConfig, config as default_config
from core.models import ProviderType
from core.services.qr_service import QrService
from core.services.tunnel_service import TunnelService
from core.services.user_service import UserService

user_service = UserService(default_config)
tunnel_service = TunnelService(default_config, user_service)
qr_service = QrService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup socket directory
    socket_dir = default_config.socket_dir
    socket_dir.mkdir(parents=True, exist_ok=True)

    # Attempt to set ownership to service_user if running as root
    if os.geteuid() == 0:
        try:
            uid = pwd.getpwnam(default_config.service_user).pw_uid
            gid = grp.getgrnam(default_config.service_group).gr_gid
            os.chown(socket_dir, uid, gid)
            os.chmod(socket_dir, 0o775)
        except Exception:
            pass

    yield

    # Cleanup socket on shutdown
    if default_config.socket_path.exists():
        try:
            default_config.socket_path.unlink()
        except Exception:
            pass


app = FastAPI(
    title="WhitelistBypass Core API",
    version=__version__,
    description="Unified local API for WhitelistBypass orchestrator, Telegram/VK bots, and web panels.",
    lifespan=lifespan,
)


class CommandExecRequest(BaseModel):
    command: str = Field(..., description="Canonical command name or alias")
    params: dict[str, Any] = Field(default_factory=dict, description="Command parameters and flags")


class SetProviderRequest(BaseModel):
    provider: str = Field(..., description="Target provider (telemost, vk, wbstream, dion)")
    rotate: bool = Field(default=False, description="Whether to immediately rotate and generate new room")


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "version": __version__,
        "users_count": len(user_service.list_users()),
    }


@app.get("/api/v1/commands")
async def get_commands():
    result = {}
    for name, spec in COMMAND_REGISTRY.items():
        result[name] = {
            "name": spec.name,
            "aliases": spec.aliases,
            "description": spec.description,
            "category": spec.category,
            "args": [
                {
                    "name": a.name,
                    "required": a.required,
                    "choices": a.choices,
                    "help": a.help,
                }
                for a in spec.args
            ],
            "options": [
                {
                    "flags": o.flags,
                    "action": o.action,
                    "default": o.default,
                    "help": o.help,
                }
                for o in spec.options
            ],
        }
    return result


@app.post("/api/v1/commands/exec")
async def execute_command(req: CommandExecRequest):
    spec = resolve_command(req.command)
    if not spec:
        raise HTTPException(status_code=400, detail=f"Unknown command '{req.command}'")

    cmd = spec.name
    params = req.params
    user = params.get("user")
    qr_flag = params.get("qr", False)

    if cmd in ("link", "get-link"):
        if not user or not user_service.user_exists(user):
            return {"success": False, "command": cmd, "user": user, "error": f"User '{user}' not found"}
        status = tunnel_service.get_status(user)
        summary = user_service.get_user_summary(user, status)
        if not summary.link:
            return {
                "success": False,
                "command": cmd,
                "user": user,
                "message": f"Link not provisioned for user '{user}'",
                "error": "No active conference link",
                "data": summary.to_dict(),
            }
        data = summary.to_dict()
        if qr_flag:
            data["qr_ansi"] = qr_service.render_ansi(summary.link)
            data["qr_png"] = qr_service.render_png_base64(summary.link)
        return {"success": True, "command": cmd, "user": user, "data": data}

    elif cmd == "qr":
        if not user or not user_service.user_exists(user):
            return {"success": False, "command": cmd, "user": user, "error": f"User '{user}' not found"}
        status = tunnel_service.get_status(user)
        summary = user_service.get_user_summary(user, status)
        if not summary.link:
            return {"success": False, "command": cmd, "user": user, "error": "Link not provisioned"}
        data = summary.to_dict()
        data["qr_ansi"] = qr_service.render_ansi(summary.link)
        data["qr_png"] = qr_service.render_png_base64(summary.link)
        return {"success": True, "command": cmd, "user": user, "data": data}

    elif cmd == "rotate":
        if not user or not user_service.user_exists(user):
            return {"success": False, "command": cmd, "user": user, "error": f"User '{user}' not found"}
        ok, new_link, err = await tunnel_service.rotate_room_async(user)
        if not ok or not new_link:
            return {"success": False, "command": cmd, "user": user, "error": err or "Rotation failed"}
        status = tunnel_service.get_status(user)
        summary = user_service.get_user_summary(user, status)
        data = summary.to_dict()
        if qr_flag:
            data["qr_ansi"] = qr_service.render_ansi(new_link)
            data["qr_png"] = qr_service.render_png_base64(new_link)
        return {"success": True, "command": cmd, "user": user, "message": "Room rotated successfully", "data": data}

    elif cmd in ("provider", "set-provider"):
        provider = params.get("provider")
        if not user or not user_service.user_exists(user):
            return {"success": False, "command": cmd, "user": user, "error": f"User '{user}' not found"}
        if not provider or provider.lower() not in ProviderType.values():
            return {
                "success": False,
                "command": cmd,
                "user": user,
                "error": f"Invalid provider '{provider}'. Supported: {', '.join(ProviderType.values())}",
            }
        provider = provider.lower()
        user_service.set_user_provider(user, provider)
        cookie = user_service.resolve_cookie_file(user, provider)
        rotate_data = None
        if params.get("rotate", False):
            ok, new_link, err = await tunnel_service.rotate_room_async(user)
            if not ok:
                return {"success": False, "command": cmd, "user": user, "error": f"Failed rotation: {err}"}
            rotate_data = {"new_link": new_link}

        status = tunnel_service.get_status(user)
        summary = user_service.get_user_summary(user, status)
        data = summary.to_dict()
        data["cookie_warning"] = not cookie.valid
        if rotate_data:
            data.update(rotate_data)
        return {"success": True, "command": cmd, "user": user, "data": data}

    elif cmd == "list":
        users = user_service.list_users()
        summaries = [
            user_service.get_user_summary(u, tunnel_service.get_status(u)).to_dict()
            for u in users
        ]
        return {"success": True, "command": cmd, "data": {"users": summaries}}

    elif cmd == "status":
        if not user or not user_service.user_exists(user):
            return {"success": False, "command": cmd, "user": user, "error": f"User '{user}' not found"}
        status = tunnel_service.get_status(user)
        summary = user_service.get_user_summary(user, status)
        conf = user_service.load_user_conf(user)
        journal = tunnel_service.get_journal(user, lines=10)
        data = summary.to_dict()
        data["config"] = conf.to_dict()
        data["journal_tail"] = journal
        return {"success": True, "command": cmd, "user": user, "data": data}

    elif cmd in ("start", "stop", "restart"):
        if not user or not user_service.user_exists(user):
            return {"success": False, "command": cmd, "user": user, "error": f"User '{user}' not found"}
        if cmd == "start":
            ok, msg = tunnel_service.start(user)
        elif cmd == "stop":
            ok, msg = tunnel_service.stop(user)
        else:
            ok, msg = tunnel_service.restart(user)
        status = tunnel_service.get_status(user)
        return {
            "success": ok,
            "command": cmd,
            "user": user,
            "message": msg,
            "data": {"service_status": status},
            "error": None if ok else msg,
        }

    elif cmd == "is-active":
        if not user:
            return {"success": False, "command": cmd, "error": "Username is required"}
        status = tunnel_service.get_status(user)
        is_active = status in ("active", "activating")
        return {"success": is_active, "command": cmd, "user": user, "data": {"active": is_active, "status": status}}

    return {"success": False, "command": cmd, "error": f"Command '{cmd}' not executable via API"}


@app.get("/api/v1/users")
async def list_users():
    users = user_service.list_users()
    summaries = [
        user_service.get_user_summary(u, tunnel_service.get_status(u)).to_dict()
        for u in users
    ]
    return {"users": summaries}


@app.get("/api/v1/users/{username}")
async def get_user_detail(username: str):
    if not user_service.user_exists(username):
        raise HTTPException(status_code=404, detail="User not found")
    status = tunnel_service.get_status(username)
    summary = user_service.get_user_summary(username, status)
    conf = user_service.load_user_conf(username)
    return {"user": summary.to_dict(), "config": conf.to_dict()}


@app.get("/api/v1/users/{username}/link")
async def get_user_link(username: str, qr: bool = Query(default=False)):
    if not user_service.user_exists(username):
        raise HTTPException(status_code=404, detail="User not found")
    status = tunnel_service.get_status(username)
    summary = user_service.get_user_summary(username, status)
    if not summary.link:
        raise HTTPException(status_code=404, detail="Conference link not provisioned")

    result = summary.to_dict()
    if qr:
        result["qr_ansi"] = qr_service.render_ansi(summary.link)
        result["qr_png"] = qr_service.render_png_base64(summary.link)
    return result


@app.get("/api/v1/users/{username}/qr")
async def get_user_qr(username: str, format: str = Query(default="ansi", pattern="^(ansi|png|svg)$")):
    if not user_service.user_exists(username):
        raise HTTPException(status_code=404, detail="User not found")
    summary = user_service.get_user_summary(username, tunnel_service.get_status(username))
    if not summary.link:
        raise HTTPException(status_code=404, detail="Conference link not provisioned")

    if format == "ansi":
        return {"qr": qr_service.render_ansi(summary.link), "link": summary.link}
    elif format == "png":
        return {"qr_base64": qr_service.render_png_base64(summary.link), "link": summary.link}
    else:
        return {"qr_svg": qr_service.render_svg(summary.link), "link": summary.link}


@app.post("/api/v1/users/{username}/rotate")
async def rotate_user_room(username: str, qr: bool = Query(default=False)):
    if not user_service.user_exists(username):
        raise HTTPException(status_code=404, detail="User not found")
    ok, new_link, err = await tunnel_service.rotate_room_async(username)
    if not ok or not new_link:
        raise HTTPException(status_code=500, detail=err or "Rotation failed")

    status = tunnel_service.get_status(username)
    summary = user_service.get_user_summary(username, status)
    result = summary.to_dict()
    if qr:
        result["qr_ansi"] = qr_service.render_ansi(new_link)
        result["qr_png"] = qr_service.render_png_base64(new_link)
    return result


@app.post("/api/v1/users/{username}/provider")
async def set_user_provider(username: str, req: SetProviderRequest):
    if not user_service.user_exists(username):
        raise HTTPException(status_code=404, detail="User not found")
    p = req.provider.lower().strip()
    if p not in ProviderType.values():
        raise HTTPException(status_code=400, detail=f"Invalid provider '{p}'")

    user_service.set_user_provider(username, p)
    if req.rotate:
        ok, _, err = await tunnel_service.rotate_room_async(username)
        if not ok:
            raise HTTPException(status_code=500, detail=f"Provider set but rotation failed: {err}")

    status = tunnel_service.get_status(username)
    return user_service.get_user_summary(username, status).to_dict()


@app.post("/api/v1/users/{username}/start")
async def start_user_service(username: str):
    if not user_service.user_exists(username):
        raise HTTPException(status_code=404, detail="User not found")
    ok, msg = tunnel_service.start(username)
    if not ok:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": tunnel_service.get_status(username)}


@app.post("/api/v1/users/{username}/stop")
async def stop_user_service(username: str):
    if not user_service.user_exists(username):
        raise HTTPException(status_code=404, detail="User not found")
    ok, msg = tunnel_service.stop(username)
    if not ok:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": tunnel_service.get_status(username)}


@app.post("/api/v1/users/{username}/restart")
async def restart_user_service(username: str):
    if not user_service.user_exists(username):
        raise HTTPException(status_code=404, detail="User not found")
    ok, msg = tunnel_service.restart(username)
    if not ok:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": tunnel_service.get_status(username)}


@app.get("/api/v1/identity")
async def resolve_identity(
    telegram_id: Optional[int] = Query(default=None),
    vk_id: Optional[int] = Query(default=None),
):
    matched_user = user_service.resolve_identity(telegram_id=telegram_id, vk_id=vk_id)
    if not matched_user:
        raise HTTPException(status_code=404, detail="Identity not mapped to any configured user")
    return {"username": matched_user}


def run_server():
    """Entrypoint to launch Uvicorn with UDS and optional HTTP."""
    cfg = default_config
    cfg.socket_dir.mkdir(parents=True, exist_ok=True)
    if cfg.socket_path.exists():
        try:
            cfg.socket_path.unlink()
        except Exception:
            pass

    print(f"[INFO] Starting WhitelistBypass Core daemon v{__version__}...")
    print(f"[INFO] Unix Domain Socket: {cfg.socket_path}")

    # Uvicorn supports uds socket path directly
    uvicorn_config = uvicorn.Config(
        app="core.app:app",
        uds=str(cfg.socket_path),
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(uvicorn_config)

    # After server binds socket, ensure permissions
    async def post_start_fix_perms():
        while not cfg.socket_path.exists():
            await asyncio.sleep(0.05)
        try:
            os.chmod(cfg.socket_path, 0o660)
            if os.geteuid() == 0:
                uid = pwd.getpwnam(cfg.service_user).pw_uid
                gid = grp.getgrnam(cfg.service_group).gr_gid
                os.chown(cfg.socket_path, uid, gid)
        except Exception:
            pass

    async def main_runner():
        asyncio.create_task(post_start_fix_perms())
        await server.serve()

    asyncio.run(main_runner())


if __name__ == "__main__":
    run_server()
