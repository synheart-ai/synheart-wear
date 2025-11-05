#!/usr/bin/env python3
"""
Synheart Wear CLI Tool

Commands for local development, testing, and operations.

Usage:
    wear start dev --vendor whoop --port 8000
    wear webhook dev --port 8000
    wear webhook inspect --limit 50
    wear pull once --vendor whoop --since 2d
    wear tokens list
    wear tokens refresh --vendor whoop --user-id abc123
    wear tokens revoke --vendor whoop --user-id abc123
"""

import os
import sys
import socket
import time
import signal
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

# Add libs to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "libs" / "py-cloud-connector"))
sys.path.insert(0, str(REPO_ROOT / "libs" / "py-normalize"))

app = typer.Typer(
    name="wear",
    help="Synheart Wear CLI - Cloud wearable integration tool",
    no_args_is_help=True,
)

console = Console()


# ============================================================================
# Helper Functions
# ============================================================================

def _is_port_available(port: int) -> bool:
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            return False

def _check_port_and_suggest(port: int) -> bool:
    """Check if port is available, suggest solution if not."""
    if _is_port_available(port):
        return True
    
    console.print(f"[red]❌ Port {port} is already in use[/red]")
    console.print()
    
    # Try to find what's using it
    import subprocess
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout:
            console.print("[yellow]Process using the port:[/yellow]")
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                console.print(f"   [dim]{lines[1]}[/dim]")
                console.print()
                console.print("[yellow]💡 Solutions:[/yellow]")
                console.print(f"   1. Kill the process: [cyan]kill $(lsof -ti :{port})[/cyan]")
                console.print(f"   2. Use a different port: [cyan]wear start dev --port 8001[/cyan]")
    except Exception:
        pass
    
    console.print()
    return False

def _show_available_data(vendor: str, port: int, base_url: str):
    """Show available users and their data counts."""
    try:
        # Check for local tokens file
        tokens_file = REPO_ROOT / "__dev__" / "tokens.json"
        if not tokens_file.exists():
            return
        
        import json
        with open(tokens_file, 'r') as f:
            tokens_data = json.load(f)
        
        # Find users for this vendor
        # Token keys are in format "vendor:user_id"
        users = []
        if isinstance(tokens_data, dict):
            for user_key, user_data in tokens_data.items():
                if isinstance(user_data, dict):
                    # Extract vendor and user_id from key format "vendor:user_id"
                    if ':' in user_key:
                        key_vendor, user_id = user_key.split(':', 1)
                        if key_vendor.lower() == vendor.lower() and user_data.get('has_tokens', False):
                            users.append(user_id)
        
        if not users:
            return
        
        console.print(f"[bold]📊 Available Data:[/bold]")
        
        # Try to fetch data counts for each user
        import httpx
        with httpx.Client(timeout=2.0) as client:
            for user_id in users[:5]:  # Limit to first 5 users
                try:
                    # Try to get recovery count as a sample
                    response = client.get(
                        f"{base_url}/v1/data/{user_id}/recovery",
                        params={"limit": 1},
                        timeout=1.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        record_count = len(data.get('records', []))
                        if record_count > 0:
                            console.print(f"   [cyan]{user_id}[/cyan]: [green]{record_count}+ records[/green]")
                except Exception:
                    pass  # Skip if can't fetch
                    
        if len(users) > 5:
            console.print(f"   ... and {len(users) - 5} more users")
        console.print()
        console.print(f"[dim]💡 Test data fetch:[/dim]")
        console.print(f"   [cyan]curl '{base_url}/v1/data/{users[0]}/recovery?limit=5'[/cyan]")
        console.print()
    except Exception:
        pass  # Silently fail if can't show data


def _open_oauth_browser(vendor: str, port: int, service_path: Optional[Path] = None):
    """Open OAuth authorization URL in default browser."""
    try:
        import webbrowser
        import httpx
    except ImportError as e:
        console.print(f"[yellow]⚠️  Required module not available: {e}[/yellow]")
        return
    
    # Determine the correct route prefix based on which service is running
    # Unified service uses: /v1/{vendor}-cloud/oauth/authorize
    # Individual vendor services (local test) use: /v1/oauth/authorize
    if service_path and (service_path / "api_local.py").exists():
        # Local test API uses simpler routes
        oauth_authorize_path = "/v1/oauth/authorize"
        oauth_callback_path = "/v1/oauth/callback"
    else:
        # Unified service uses vendor-prefixed routes
        oauth_authorize_path = f"/v1/{vendor}-cloud/oauth/authorize"
        oauth_callback_path = f"/v1/{vendor}-cloud/oauth/callback"
    
    # Generate redirect URI and state
    redirect_uri = f"http://localhost:{port}{oauth_callback_path}"
    state = f"dev_user_{int(time.time())}"
    
    # First, call the local API endpoint to get the actual WHOOP authorization URL
    local_endpoint = f"http://localhost:{port}{oauth_authorize_path}"
    params = {
        "redirect_uri": redirect_uri,
        "state": state,
    }
    
    console.print()
    console.print("[bold green]🌐 Getting OAuth authorization URL...[/bold green]")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(local_endpoint, params=params)
            if response.status_code != 200:
                console.print(f"[red]❌ Failed to get authorization URL: {response.status_code}[/red]")
                console.print(f"   Response: {response.text[:200]}")
                return
            
            data = response.json()
            whoop_auth_url = data.get("authorization_url")
            
            if not whoop_auth_url:
                console.print(f"[red]❌ No authorization_url in response[/red]")
                console.print(f"   Response: {data}")
                return
            
            # Now open the actual WHOOP authorization URL
            console.print(f"[green]✅ Got authorization URL[/green]")
            console.print(f"   Opening: [cyan]{whoop_auth_url[:80]}...[/cyan]")
            console.print()
    
            # Try to open browser - use multiple methods for better compatibility
            opened = False
            
            # Method 1: Python webbrowser module
            try:
                opened = webbrowser.open(whoop_auth_url)
                if opened:
                    console.print("[green]✅ Browser opened successfully[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️  webbrowser.open() failed: {e}[/yellow]")
            
            # Method 2: macOS 'open' command (fallback)
            if not opened:
                import platform
                if platform.system() == "Darwin":  # macOS
                    import subprocess
                    try:
                        subprocess.run(["open", whoop_auth_url], check=True, timeout=2)
                        console.print("[green]✅ Browser opened via 'open' command[/green]")
                        opened = True
                    except Exception as e:
                        console.print(f"[yellow]⚠️  'open' command failed: {e}[/yellow]")
            
            # Method 3: Linux xdg-open
            if not opened:
                import platform
                if platform.system() == "Linux":
                    import subprocess
                    try:
                        subprocess.run(["xdg-open", whoop_auth_url], check=True, timeout=2)
                        console.print("[green]✅ Browser opened via 'xdg-open'[/green]")
                        opened = True
                    except Exception as e:
                        console.print(f"[yellow]⚠️  'xdg-open' failed: {e}[/yellow]")
            
            if not opened:
                console.print()
                console.print("[yellow]⚠️  Could not automatically open browser[/yellow]")
                console.print(f"   Please open manually: [cyan]{whoop_auth_url}[/cyan]")
            
            console.print()
            console.print("[yellow]📝 Instructions:[/yellow]")
            console.print("   1. Log in to your WHOOP account in the browser")
            console.print("   2. Click 'Authorize' to grant access")
            console.print(f"   3. You'll be redirected to: {redirect_uri}")
            console.print("   4. Check logs below for OAuth completion status")
            console.print()
            
    except httpx.RequestError as e:
        console.print(f"[red]❌ Failed to connect to server: {e}[/red]")
        console.print(f"   Make sure the server is running on port {port}")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


# ============================================================================
# START Command - Local Development Server
# ============================================================================

@app.command()
def start(
    mode: str = typer.Argument("dev", help="Mode: dev or live"),
    vendor: Optional[str] = typer.Option(None, "--vendor", "-v", help="Vendor to run (whoop, garmin, all)"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to run on"),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Auto-reload on code changes"),
    env_file: Optional[str] = typer.Option(None, "--env", help="Environment file (.env.production, .env.test)"),
    open_browser: bool = typer.Option(False, "--open-browser", help="Open OAuth authorization URL in default browser"),
    webhook_record: bool = typer.Option(True, "--webhook-record/--no-webhook-record", help="Enable webhook recording (dev mode only)"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose logging"),
):
    """
    Unified command to start Synheart Wear service.
    
    In dev mode: Enables auto-reload, webhook recording, verbose logging.
    In live mode: Production-optimized settings.
    
    Examples:
        wear start dev --vendor whoop --open-browser
        wear start dev --port 8000 --verbose
        wear start live --vendor all
    """
    # Print startup banner
    console.print()
    console.print("[bold green]🚀 Starting Synheart Wear[/bold green]")
    console.print("━" * 60)
    console.print()
    console.print(f"[bold]📍 Configuration:[/bold]")
    console.print(f"   Mode:           [cyan]{mode}[/cyan]")
    console.print(f"   Vendor:         [cyan]{vendor or 'all'}[/cyan]")
    console.print(f"   Port:           [cyan]{port}[/cyan]")
    console.print(f"   Auto-reload:    {'✅ enabled' if reload and mode == 'dev' else '❌ disabled'}")
    console.print(f"   Webhook record: {'✅ enabled' if webhook_record and mode == 'dev' else '❌ disabled'}")
    if verbose:
        console.print(f"   Verbose:        [cyan]✅ enabled[/cyan]")
    console.print()

    # Determine which service to run
    if vendor == "whoop":
        service_path = REPO_ROOT / "services" / "whoop-cloud"
        script = "api_local.py" if mode == "dev" else "api.py"
    elif vendor == "garmin":
        service_path = REPO_ROOT / "services" / "garmin-cloud"
        script = "api_local.py" if mode == "dev" else "api.py"
    else:
        # Run unified service
        service_path = REPO_ROOT / "services" / "synheart-wear-service"
        script = "api.py"

    if not service_path.exists():
        console.print(f"[red]❌ Service directory not found: {service_path}[/red]")
        raise typer.Exit(1)

    script_path = service_path / script
    if not script_path.exists():
        console.print(f"[red]❌ Script not found: {script_path}[/red]")
        raise typer.Exit(1)

    # Set environment
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{REPO_ROOT}/libs/py-cloud-connector:{REPO_ROOT}/libs/py-normalize:{env.get('PYTHONPATH', '')}"
    
    # Enable dev mode features
    if mode == "dev":
        env["DEV_MODE"] = "true"
        if webhook_record:
            env["WEBHOOK_RECORD"] = "true"
            # Ensure __dev__ directory exists
            dev_dir = REPO_ROOT / "__dev__"
            dev_dir.mkdir(exist_ok=True)
            env["WEBHOOK_RECORD_PATH"] = str(dev_dir / "webhooks_recent.jsonl")
        if verbose:
            env["LOG_LEVEL"] = "DEBUG"
    
    # Load environment file
    # Priority: --env flag > .env.local (dev mode) > .env (any mode) > default (.env.production for whoop-cloud)
    # Ensure env_file is a string, not a Typer OptionInfo object
    if env_file and isinstance(env_file, str):
        env_path = service_path / env_file
        if env_path.exists():
            console.print(f"[green]📝 Loading environment from:[/green] [cyan]{env_file}[/cyan]")
            from dotenv import load_dotenv
            load_dotenv(env_path, override=True)
        else:
            console.print(f"[yellow]⚠️  Environment file not found: {env_file}[/yellow]")
    else:
        # Auto-detect environment file in dev mode
        # Priority: service directory > repo root (for shared credentials)
        env_files_to_try = []
        if mode == "dev":
            # Try service-specific first, then root
            env_files_to_try = [
                (service_path / ".env.local"),
                (service_path / ".env.dev"),
                (service_path / ".env"),
                (REPO_ROOT / ".env.local"),  # Shared root-level file
                (REPO_ROOT / ".env"),
            ]
        else:
            env_files_to_try = [
                (service_path / ".env.production"),
                (service_path / ".env"),
                (REPO_ROOT / ".env.production"),
                (REPO_ROOT / ".env"),
            ]
        
        from dotenv import load_dotenv
        env_loaded = False
        for env_path in env_files_to_try:
            if env_path.exists():
                load_dotenv(env_path, override=True)
                rel_path = env_path.relative_to(REPO_ROOT)
                console.print(f"[green]📝 Auto-loaded environment from:[/green] [cyan]{rel_path}[/cyan]")
                env_loaded = True
                break
        
        if not env_loaded:
            console.print(f"[dim]💡 No environment file found. Using system environment variables.[/dim]")
            console.print(f"   Create [cyan].env.local[/cyan] in repo root or service directory")
            console.print(f"   Or use: [cyan]wear start {mode} --env .env.local[/cyan]")
    
    # Determine route prefix based on service type
    is_local_test = script == "api_local.py"
    
    # Display endpoints
    console.print(f"[bold]🌐 Endpoints:[/bold]")
    base_url = f"http://localhost:{port}"
    console.print(f"   API Docs:      [cyan]{base_url}/docs[/cyan]")
    console.print(f"   Health Check:  [cyan]{base_url}/health[/cyan]")
    if vendor and vendor != "all":
        if is_local_test:
            console.print(f"   OAuth Auth:    [cyan]{base_url}/v1/oauth/authorize[/cyan]")
            console.print(f"   Webhooks:      [cyan]{base_url}/v1/webhooks/{vendor}[/cyan]")
        else:
            console.print(f"   OAuth Auth:    [cyan]{base_url}/v1/{vendor}-cloud/oauth/authorize[/cyan]")
            console.print(f"   Webhooks:      [cyan]{base_url}/v1/{vendor}-cloud/webhooks/{vendor}[/cyan]")
    else:
        console.print(f"   Webhooks:      [cyan]{base_url}/v1/{{vendor}}-cloud/webhooks/{{vendor}}[/cyan]")
    console.print()
    
    # Show available users and data (dev mode only)
    if mode == "dev" and vendor:
        _show_available_data(vendor, port, base_url)
    
    # Webhook recording info
    if webhook_record and mode == "dev":
        console.print(f"[green]💾 Webhook recording enabled[/green]")
        console.print(f"   Saving to: [cyan]__dev__/webhooks_recent.jsonl[/cyan]")
        console.print(f"   Inspect with: [cyan]wear webhook inspect[/cyan]")
        console.print()
    
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()
    
    # Check if port is available before starting
    if not _check_port_and_suggest(port):
        raise typer.Exit(1)

    # ngrok is REQUIRED for dev mode
    if mode == "dev":
        try:
            from pyngrok import ngrok
        except ImportError:
            console.print("[red]❌ pyngrok is required for dev mode[/red]")
            console.print()
            console.print("[yellow]💡 Install pyngrok:[/yellow]")
            console.print("   [cyan]pip install pyngrok[/cyan]")
            console.print()
            console.print("pyngrok is needed to expose your local server so the SDK can pull data.")
            raise typer.Exit(1)
        
        # Check if ngrok is already running for this port
        ngrok_running = False
        ngrok_url = None
        existing_tunnel = None
        try:
            # Get all active tunnels
            tunnels = ngrok.get_tunnels()
            for tunnel in tunnels:
                # Check if tunnel is for our port
                tunnel_addr = tunnel.config.get("addr", "")
                if f":{port}" in tunnel_addr or f"localhost:{port}" in tunnel_addr:
                    ngrok_running = True
                    ngrok_url = tunnel.public_url
                    existing_tunnel = tunnel
                    console.print(f"[green]✅ ngrok tunnel found:[/green] [cyan]{ngrok_url}[/cyan]")
                    console.print(f"   [dim]Reusing existing tunnel for port {port}[/dim]")
                    console.print()
                    console.print(f"[bold]📱 SDK Configuration:[/bold]")
                    console.print(f"   Use this URL in your Flutter app:")
                    console.print(f"   [cyan]baseUrl: '{ngrok_url}'[/cyan]")
                    console.print()
                    break
        except Exception as e:
            # If we can't get tunnels, that's okay - we'll try to start fresh
            pass
        
        # Start ngrok if not running
        if not ngrok_running:
            console.print("[bold]🌐 Starting ngrok tunnel...[/bold]")
            try:
                # Start ngrok tunnel
                tunnel = ngrok.connect(port, "http")
                ngrok_url = tunnel.public_url
                
                console.print(f"[green]✅ ngrok tunnel started:[/green] [cyan]{ngrok_url}[/cyan]")
                console.print()
                console.print(f"[bold]📱 SDK Configuration:[/bold]")
                console.print(f"   Use this URL in your Flutter app:")
                console.print(f"   [cyan]baseUrl: '{ngrok_url}'[/cyan]")
                console.print()
                
                # Store tunnel for cleanup
                env["NGROK_TUNNEL"] = tunnel.name
                
            except Exception as e:
                error_str = str(e)
                # Check if error is about existing endpoint
                if "already online" in error_str or "ERR_NGROK_334" in error_str:
                    console.print(f"[yellow]⚠️  ngrok endpoint conflict detected[/yellow]")
                    console.print()
                    console.print("[yellow]💡 Trying to resolve...[/yellow]")
                    
                    # Try to disconnect all existing tunnels first
                    try:
                        # Get all tunnels and disconnect them individually
                        tunnels = ngrok.get_tunnels()
                        if tunnels:
                            for tunnel in tunnels:
                                try:
                                    ngrok.disconnect(tunnel.public_url)
                                    console.print(f"[dim]   Disconnected tunnel: {tunnel.public_url}[/dim]")
                                except Exception:
                                    pass
                        
                        # Also try to kill the ngrok process
                        ngrok.kill()
                        console.print("[dim]   Killed local ngrok process[/dim]")
                        
                        # Wait longer for cleanup (remote endpoint might need time)
                        import time
                        time.sleep(2)
                        
                        # Try to start again
                        tunnel = ngrok.connect(port, "http")
                        ngrok_url = tunnel.public_url
                        
                        console.print(f"[green]✅ ngrok tunnel started:[/green] [cyan]{ngrok_url}[/cyan]")
                        console.print()
                        console.print(f"[bold]📱 SDK Configuration:[/bold]")
                        console.print(f"   Use this URL in your Flutter app:")
                        console.print(f"   [cyan]baseUrl: '{ngrok_url}'[/cyan]")
                        console.print()
                        
                        env["NGROK_TUNNEL"] = tunnel.name
                        
                    except Exception as e2:
                        # If auto-resolution fails, extract the conflicting endpoint from error
                        import re
                        endpoint_match = re.search(r"https://([a-zA-Z0-9\-]+\.ngrok-free\.dev)", error_str)
                        conflicting_endpoint = endpoint_match.group(1) if endpoint_match else None
                        
                        console.print(f"[red]❌ Could not resolve ngrok conflict[/red]")
                        if conflicting_endpoint:
                            console.print(f"   [dim]Conflicting endpoint: {conflicting_endpoint}[/dim]")
                        console.print()
                        console.print("[yellow]💡 This usually means:[/yellow]")
                        console.print("   • An ngrok tunnel is running in another terminal")
                        console.print("   • A reserved domain is already in use")
                        console.print("   • An ngrok agent is running elsewhere")
                        console.print()
                        console.print("[yellow]💡 Manual fixes:[/yellow]")
                        console.print("   1. [bold]Stop all ngrok processes:[/bold]")
                        console.print("      [cyan]pkill -f ngrok[/cyan]  # or [cyan]ngrok kill[/cyan]")
                        console.print()
                        console.print("   2. [bold]Use a different port:[/bold]")
                        console.print(f"      [cyan]wear start dev --port {port + 1}[/cyan]")
                        console.print()
                        console.print("   3. [bold]Start ngrok manually first:[/bold]")
                        console.print(f"      [cyan]ngrok http {port}[/cyan]")
                        console.print("      Then run: [cyan]wear start dev --port {port}[/cyan]")
                        console.print()
                        console.print("   4. [bold]Check for running ngrok:[/bold]")
                        console.print("      [cyan]ps aux | grep ngrok[/cyan]")
                        raise typer.Exit(1)
                else:
                    console.print(f"[red]❌ Could not start ngrok: {e}[/red]")
                    console.print()
                    console.print("[yellow]💡 Troubleshooting:[/yellow]")
                    console.print("   1. Make sure you have an ngrok account (free): https://ngrok.com/")
                    console.print("   2. Set your authtoken: [cyan]ngrok config add-authtoken YOUR_TOKEN[/cyan]")
                    console.print("   3. Or install pyngrok: [cyan]pip install pyngrok[/cyan]")
                    raise typer.Exit(1)

    import subprocess
    import threading
    import time as time_module

    # If browser opening is requested, start server first then open browser
    if open_browser and vendor and vendor != "all":
        def open_browser_after_start():
            # Wait for server to be ready - try to connect to health endpoint
            import httpx
            max_retries = 10
            for i in range(max_retries):
                try:
                    response = httpx.get(f"http://localhost:{port}/health", timeout=1.0)
                    if response.status_code == 200:
                        # Server is ready, open browser
                        time_module.sleep(0.5)  # Small additional delay
                        _open_oauth_browser(vendor, port, service_path)
                        return
                except Exception:
                    pass
                time_module.sleep(0.5)
            
            # Fallback: if health check fails, try opening anyway after timeout
            console.print("[yellow]⚠️  Server may not be fully ready, opening browser anyway...[/yellow]")
            _open_oauth_browser(vendor, port, service_path)
        
        browser_thread = threading.Thread(target=open_browser_after_start, daemon=True)
        browser_thread.start()

    cmd = [
        "uvicorn",
        f"{script_path.stem}:app",
        "--host", "0.0.0.0",
        "--port", str(port),
    ]

    if reload and mode == "dev":
        cmd.extend(["--reload", "--reload-dir", str(service_path)])

    # Store ngrok tunnel info for cleanup
    ngrok_tunnel_url = None
    if mode == "dev" and "NGROK_TUNNEL" in env:
        # Try to get the tunnel URL from the tunnel name
        try:
            from pyngrok import ngrok
            tunnel_name = env.get("NGROK_TUNNEL")
            tunnels = ngrok.get_tunnels()
            for tunnel in tunnels:
                if tunnel.name == tunnel_name:
                    ngrok_tunnel_url = tunnel.public_url
                    break
        except Exception:
            pass

    # Cleanup function for ngrok
    def cleanup_ngrok():
        """Clean up ngrok tunnel on exit."""
        if ngrok_tunnel_url:
            try:
                from pyngrok import ngrok
                ngrok.disconnect(ngrok_tunnel_url)
            except Exception:
                pass  # Ignore cleanup errors
    
    # Register cleanup for normal exit
    import atexit
    atexit.register(cleanup_ngrok)
    
    # Use Popen instead of run for better signal control
    process = None
    try:
        process = subprocess.Popen(cmd, cwd=service_path, env=env)
        
        # Signal handler for Ctrl+C (must be defined after process is created)
        def signal_handler(sig, frame):
            """Handle SIGINT (Ctrl+C) to clean up both processes."""
            console.print("\n\n👋 Shutting down...")
            cleanup_ngrok()
            console.print("[dim]ngrok tunnel stopped[/dim]")
            # Terminate the uvicorn process
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
            # Exit gracefully
            sys.exit(0)
        
        # Register signal handler
        signal.signal(signal.SIGINT, signal_handler)
        
        # Wait for process to complete
        process.wait()
    except KeyboardInterrupt:
        # Fallback if signal handler doesn't catch it
        console.print("\n\n👋 Server stopped")
        cleanup_ngrok()
        console.print("[dim]ngrok tunnel stopped[/dim]")
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
    except subprocess.CalledProcessError as e:
        console.print(f"\n[red]❌ Server failed with exit code {e.returncode}[/red]")
        cleanup_ngrok()
        raise typer.Exit(e.returncode)


# ============================================================================
# WEBHOOK Commands
# ============================================================================

webhook_app = typer.Typer(help="Webhook testing and inspection")
app.add_typer(webhook_app, name="webhook")


@webhook_app.command("dev")
def webhook_dev(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run webhook receiver"),
    vendor: str = typer.Option("all", "--vendor", "-v", help="Vendor to receive webhooks from"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save webhooks to __dev__/webhooks_recent.jsonl"),
):
    """
    Start webhook development server with recording.

    Example:
        wear webhook dev --port 8000 --vendor whoop
    """
    console.print("🎣 Starting webhook development server...")
    console.print(f"📍 Vendor: [cyan]{vendor}[/cyan]")
    console.print(f"🔌 Port: [cyan]{port}[/cyan]")

    if save:
        console.print("💾 Recording webhooks to: [cyan]__dev__/webhooks_recent.jsonl[/cyan]")

    console.print()
    console.print("[yellow]⚠️  Note: This is a development server with webhook recording enabled.[/yellow]")
    console.print("[yellow]   Use 'wear start dev' for full API functionality.[/yellow]")
    console.print()

    # Use regular start command but with webhook recording enabled
    os.environ["DEV_MODE"] = "true"
    os.environ["WEBHOOK_RECORD"] = "true" if save else "false"

    # Call start command with all parameters explicitly set
    start(
        mode="dev",
        vendor=vendor,
        port=port,
        reload=True,
        env_file=None,
        open_browser=False,
        webhook_record=save,
        verbose=False,
    )


@webhook_app.command("inspect")
def webhook_inspect(
    limit: int = typer.Option(50, "--limit", "-n", help="Number of webhooks to show"),
    vendor: Optional[str] = typer.Option(None, "--vendor", "-v", help="Filter by vendor"),
    event_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by event type"),
):
    """
    Inspect recent webhooks from dev mode.

    Example:
        wear webhook inspect --limit 50
        wear webhook inspect --vendor whoop --type recovery.updated
    """
    console.print("🔍 Inspecting recent webhooks...")
    console.print()

    webhooks_file = REPO_ROOT / "__dev__" / "webhooks_recent.jsonl"

    if not webhooks_file.exists():
        console.print("[yellow]⚠️  No webhook recording file found.[/yellow]")
        console.print(f"   Expected at: {webhooks_file}")
        console.print()
        console.print("   Run [cyan]wear webhook dev[/cyan] to start recording webhooks.")
        raise typer.Exit(1)

    import json

    # Read webhooks
    webhooks = []
    with open(webhooks_file, 'r') as f:
        for line in f:
            try:
                webhook = json.loads(line.strip())

                # Apply filters
                if vendor and webhook.get('vendor') != vendor:
                    continue
                if event_type and webhook.get('type') != event_type:
                    continue

                webhooks.append(webhook)
            except json.JSONDecodeError:
                continue

    # Get last N webhooks
    webhooks = webhooks[-limit:]

    if not webhooks:
        console.print("[yellow]No webhooks found matching filters.[/yellow]")
        raise typer.Exit(0)

    # Display table
    table = Table(title=f"Recent Webhooks (last {len(webhooks)})")
    table.add_column("Timestamp", style="dim")
    table.add_column("Vendor", style="cyan")
    table.add_column("Event Type", style="yellow")
    table.add_column("User ID", style="green")
    table.add_column("Resource ID", style="magenta")

    for webhook in webhooks:
        table.add_row(
            webhook.get('timestamp', 'N/A'),
            webhook.get('vendor', 'N/A'),
            webhook.get('type', 'N/A'),
            webhook.get('user_id', 'N/A'),
            webhook.get('resource_id', 'N/A'),
        )

    console.print(table)
    console.print()
    console.print(f"📊 Showing {len(webhooks)} webhooks")


# ============================================================================
# PULL Command - Manual Data Sync
# ============================================================================

@app.command()
def pull(
    mode: str = typer.Argument("once", help="Mode: once or continuous"),
    vendor: str = typer.Option(..., "--vendor", "-v", help="Vendor to pull from (whoop, garmin)"),
    user_id: Optional[str] = typer.Option(None, "--user-id", "-u", help="Specific user ID to pull"),
    since: Optional[str] = typer.Option(None, "--since", "-s", help="Time range (e.g., 2d, 1w, 2024-01-01)"),
    limit: int = typer.Option(25, "--limit", "-n", help="Max records to fetch per resource type (max: 25)"),
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed output"),
):
    """
    Trigger manual data pull (backfill).

    Examples:
        wear pull once --vendor whoop --since 2d
        wear pull once --vendor garmin --user-id abc123 --since 1w
    """
    console.print(f"📥 Triggering data pull from [bold]{vendor}[/bold]...")

    if user_id:
        console.print(f"👤 User: [cyan]{user_id}[/cyan]")
    else:
        console.print("👥 All users")

    if since:
        console.print(f"📅 Since: [cyan]{since}[/cyan]")

    console.print(f"📊 Limit: [cyan]{limit}[/cyan] records")
    console.print()

    # Build API request
    import httpx
    
    def _parse_since_parameter(since_str: str) -> str:
        """Parse since parameter (e.g., '7d', '2w', '2024-01-01') to ISO8601."""
        from datetime import datetime, timedelta, timezone
        since_str = since_str.strip().lower()
        
        if since_str.endswith('d'):
            days = int(since_str[:-1])
            dt = datetime.now(timezone.utc) - timedelta(days=days)
            return dt.isoformat()
        elif since_str.endswith('w'):
            weeks = int(since_str[:-1])
            dt = datetime.now(timezone.utc) - timedelta(weeks=weeks)
            return dt.isoformat()
        elif since_str.endswith('h'):
            hours = int(since_str[:-1])
            dt = datetime.now(timezone.utc) - timedelta(hours=hours)
            return dt.isoformat()
        else:
            # Try parsing as ISO8601 date
            try:
                # If it's just a date, add time
                if 'T' not in since_str:
                    since_str = f"{since_str}T00:00:00Z"
                # Validate it's ISO8601
                datetime.fromisoformat(since_str.replace('Z', '+00:00'))
                return since_str
            except ValueError:
                # Default to 7 days ago if can't parse
                dt = datetime.now(timezone.utc) - timedelta(days=7)
                return dt.isoformat()
    
    # Determine the correct endpoint based on service type
    # Local test APIs use: /v1/pull/{user_id}
    # Unified service uses: /v1/{vendor}-cloud/pull
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    # Check if we're hitting a local test API (simpler routes)
    # For local test, we need user_id in the path
    if not user_id:
        console.print("[red]❌ --user-id is required for pull command[/red]")
        console.print("   Example: [cyan]wear pull once --vendor whoop --user-id abc123 --since 7d[/cyan]")
        raise typer.Exit(1)
    
    # Try local endpoint format first (for api_local.py)
    # Format: POST /v1/pull/{user_id}?since=...&limit=...
    local_endpoint = f"{api_url}/v1/pull/{user_id}"
    
    # Unified service endpoint format
    unified_endpoint = f"{api_url}/v1/{vendor}-cloud/pull"
    
    params = {
        "limit": limit,
    }
    if since:
        # Parse since parameter to ISO8601 format if needed
        since_iso = _parse_since_parameter(since)
        params["since"] = since_iso
    
    # Also add resource_types to pull all data types
    params["resource_types"] = ["recovery", "sleep", "workout", "cycle"]

    # Try local endpoint first (for api_local_test.py)
    console.print(f"🔗 Calling: [dim]{local_endpoint}[/dim]")
    console.print()

    # First, verify tokens by fetching user profile
    profile_endpoint = f"{api_url}/v1/data/{user_id}/profile"
    try:
        profile_response = httpx.get(profile_endpoint, timeout=10.0)
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            if verbose:
                console.print(f"[dim]✓ Profile verified: {profile_data.get('user_id', 'N/A')}[/dim]")
        elif profile_response.status_code == 401:
            console.print("[red]❌ Authentication failed - tokens expired or invalid[/red]")
            console.print("   Please re-authenticate: [cyan]wear start dev --open-browser[/cyan]")
            raise typer.Exit(1)
        else:
            # Show warning for non-200/non-401 status codes
            console.print(f"[yellow]⚠️  Profile check returned {profile_response.status_code}[/yellow]")
            # Try to extract and show error details
            is_actual_401 = False
            try:
                error_data = profile_response.json()
                if isinstance(error_data, dict):
                    detail = error_data.get("detail")
                    if isinstance(detail, dict):
                        # Check if the underlying WHOOP API error is 401
                        if "401" in str(detail.get("message", "")) or detail.get("status_code") == 401:
                            is_actual_401 = True
                        error_msg = detail.get("message") or detail.get("error") or str(detail)
                    else:
                        error_msg = detail
                    if error_msg:
                        console.print(f"   [dim]Error: {error_msg}[/dim]")
            except Exception:
                # If JSON parsing fails, show first 200 chars of text
                error_text = profile_response.text[:200] if profile_response.text else "No error details"
                if error_text:
                    console.print(f"   [dim]Response: {error_text}[/dim]")
            
            # If the underlying error is 401, treat it as authentication issue
            if is_actual_401:
                console.print(f"   [yellow]⚠️  Profile endpoint requires authentication - tokens may need refresh[/yellow]")
                console.print(f"   [dim]Note: Pull operation may still work if tokens are valid for data endpoints[/dim]")
            else:
                console.print(f"   [dim]Note: This is non-fatal - pull will continue anyway[/dim]")
    except httpx.RequestError as e:
        console.print(f"[yellow]⚠️  Profile check failed: Could not connect to {profile_endpoint}[/yellow]")
        console.print(f"   [dim]Error: {e}[/dim]")
        console.print(f"   [dim]Note: This is non-fatal - pull will continue anyway[/dim]")
    except Exception as e:
        console.print(f"[yellow]⚠️  Profile check failed (non-fatal): {e}[/yellow]")

    try:
        with console.status("[bold green]Pulling data..."):
            # Try local endpoint format first (for api_local.py)
            try:
                response = httpx.post(local_endpoint, params=params, timeout=300.0)
                if response.status_code == 200:
                    endpoint_used = local_endpoint
                else:
                    # Try unified endpoint format
                    response = httpx.post(unified_endpoint, params=params, timeout=300.0)
                    endpoint_used = unified_endpoint
            except httpx.HTTPError:
                # If local fails, try unified
                response = httpx.post(unified_endpoint, params=params, timeout=300.0)
                endpoint_used = unified_endpoint

        if response.status_code == 200:
            data = response.json()
            console.print("[green]✅ Pull completed successfully![/green]")
            console.print()
            
            # Display summary
            total_records = data.get('total_records', 0)
            pull_type = data.get('pull_type', 'unknown')
            
            console.print(f"[bold]📊 Pull Summary:[/bold]")
            console.print(f"   Type:        [cyan]{pull_type}[/cyan]")
            if data.get('since'):
                console.print(f"   Since:       [cyan]{data.get('since')}[/cyan]")
            console.print(f"   Total records: [bold]{total_records}[/bold]")
            
            # Show breakdown by resource type if available
            if 'results' in data:
                console.print()
                console.print("[bold]📦 Breakdown by resource:[/bold]")
                for resource_type, result in data['results'].items():
                    records = result.get('records', 0)
                    if records > 0:
                        console.print(f"   [green]✓ {resource_type:12}[/green] [cyan]{records:3}[/cyan] records")
                    else:
                        console.print(f"   [dim]  {resource_type:12}[/dim] [dim]0[/dim] records")
            
            # Legacy fields (for compatibility)
            if 'records_fetched' in data:
                console.print()
                console.print(f"📊 Records fetched: [bold]{data.get('records_fetched', 0)}[/bold]")
            if 'records_stored' in data:
                console.print(f"💾 Records stored: [bold]{data.get('records_stored', 0)}[/bold]")
            if 'duration_seconds' in data:
                console.print(f"⏱️  Duration: [bold]{data.get('duration_seconds', 0):.2f}s[/bold]")
            
            # Warn if no records
            if total_records == 0:
                console.print()
                console.print("[yellow]⚠️  No records found[/yellow]")
                console.print("   Possible reasons:")
                console.print("   • No data in the specified time range")
                console.print("   • User has no connected data")
                console.print(f"   • Try a different time range: [cyan]wear pull once --vendor whoop --user-id {user_id} --since 30d[/cyan]")
                
                # Show detailed results for debugging
                if verbose and 'results' in data:
                    console.print()
                    console.print("[bold]🔍 Detailed Results:[/bold]")
                    for resource_type, result in data['results'].items():
                        if 'error' in result:
                            console.print(f"   [red]✗ {resource_type}:[/red] {result['error']}")
                        else:
                            records = result.get('records', 0)
                            console.print(f"   [green]✓ {resource_type}:[/green] {records} records")
                    
        else:
            # Show error details
            console.print(f"[red]❌ Pull failed with status {response.status_code}[/red]")
            try:
                error_data = response.json()
                console.print(f"   Error: {error_data}")
            except:
                console.print(f"   Response: {response.text[:500]}")
            
            if verbose:
                console.print()
                console.print("[dim]Request details:[/dim]")
                console.print(f"   Endpoint: {endpoint_used if 'endpoint_used' in locals() else local_endpoint}")
                console.print(f"   Params: {params}")
            
            raise typer.Exit(1)
            
    except httpx.HTTPStatusError as e:
        console.print(f"[red]❌ HTTP error: {e.response.status_code}[/red]")
        try:
            error_data = e.response.json()
            console.print(f"   Error: {error_data}")
        except:
            console.print(f"   Response: {e.response.text[:500]}")
        raise typer.Exit(1)
    except httpx.ConnectError:
        console.print(f"[red]❌ Cannot connect to API at {api_url}[/red]")
        console.print()
        console.print("Make sure the server is running:")
        console.print(f"  [cyan]wear start dev --vendor {vendor}[/cyan]")
        raise typer.Exit(1)
    except httpx.RequestError as e:
        console.print(f"[red]❌ Request failed: {e}[/red]")
        console.print(f"   Make sure the server is running: [cyan]wear start dev[/cyan]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        if verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


# ============================================================================
# TOKENS Commands - Token Management
# ============================================================================

tokens_app = typer.Typer(help="OAuth token management")
app.add_typer(tokens_app, name="tokens")


@tokens_app.command("list")
def tokens_list(
    vendor: Optional[str] = typer.Option(None, "--vendor", "-v", help="Filter by vendor"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max tokens to show"),
):
    """
    List stored OAuth tokens.

    Example:
        wear tokens list
        wear tokens list --vendor whoop
        wear tokens list --status active
    """
    console.print("🔑 Listing OAuth tokens...")
    console.print()

    # Query DynamoDB (or mock store in dev)
    from synheart_cloud_connector.tokens import TokenStore

    table_name = os.getenv("DYNAMODB_TABLE", "test_cloud_connector_tokens")
    kms_key_id = os.getenv("KMS_KEY_ID")

    try:
        store = TokenStore(table_name=table_name, kms_key_id=kms_key_id)

        # Get tokens (this would need a scan method in TokenStore)
        console.print("[yellow]⚠️  Token listing not yet implemented in TokenStore[/yellow]")
        console.print()
        console.print("This command will:")
        console.print("  • Query DynamoDB for all tokens")
        console.print("  • Show vendor, user_id, status, expires_at")
        console.print("  • Filter by vendor/status")
        console.print()
        console.print("Implementation needed in TokenStore.scan() method")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@tokens_app.command("refresh")
def tokens_refresh(
    vendor: str = typer.Option(..., "--vendor", "-v", help="Vendor (whoop, garmin)"),
    user_id: str = typer.Option(..., "--user-id", "-u", help="User ID"),
):
    """
    Refresh OAuth token for a user.

    Example:
        wear tokens refresh --vendor whoop --user-id abc123
    """
    console.print(f"🔄 Refreshing token for [cyan]{vendor}[/cyan] user [cyan]{user_id}[/cyan]...")
    console.print()

    from synheart_cloud_connector.tokens import TokenStore
    from synheart_cloud_connector.vendor_types import VendorType

    table_name = os.getenv("DYNAMODB_TABLE", "test_cloud_connector_tokens")
    kms_key_id = os.getenv("KMS_KEY_ID")

    try:
        store = TokenStore(table_name=table_name, kms_key_id=kms_key_id)

        # Get current tokens
        # VendorType enum values are lowercase ("whoop", "garmin")
        vendor_enum = VendorType(vendor.lower())
        tokens = store.get_tokens(vendor_enum, user_id)

        if not tokens:
            console.print(f"[red]❌ No tokens found for {vendor}:{user_id}[/red]")
            raise typer.Exit(1)

        # Refresh would happen here
        console.print("[yellow]⚠️  Token refresh not yet implemented[/yellow]")
        console.print()
        console.print("This command will:")
        console.print("  • Get current tokens from DynamoDB")
        console.print("  • Call vendor's refresh endpoint")
        console.print("  • Save new tokens back to DynamoDB")
        console.print()
        console.print("Implementation needed in connector.refresh_token() method")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@tokens_app.command("revoke")
def tokens_revoke(
    vendor: str = typer.Option(..., "--vendor", "-v", help="Vendor (whoop, garmin)"),
    user_id: str = typer.Option(..., "--user-id", "-u", help="User ID"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed error messages"),
):
    """
    Revoke OAuth token for a user.

    Example:
        wear tokens revoke --vendor whoop --user-id abc123 --yes
    """
    if not confirm:
        confirm = typer.confirm(
            f"Are you sure you want to revoke tokens for {vendor}:{user_id}?"
        )
        if not confirm:
            console.print("Cancelled.")
            raise typer.Exit(0)

    console.print(f"🗑️  Revoking token for [cyan]{vendor}[/cyan] user [cyan]{user_id}[/cyan]...")
    console.print()

    from synheart_cloud_connector.vendor_types import VendorType

    # VendorType enum values are lowercase ("whoop", "garmin")
    vendor_enum = VendorType(vendor.lower())
    token_key = f"{vendor_enum.value}:{user_id}"

    # Try to use local file-based storage first (for dev mode)
    tokens_file = REPO_ROOT / "__dev__" / "tokens.json"
    
    # Check if local tokens file exists and we're not explicitly using DynamoDB
    table_name = os.getenv("DYNAMODB_TABLE", "test_cloud_connector_tokens")
    use_dynamodb = os.getenv("USE_DYNAMODB", "false").lower() == "true" or table_name != "test_cloud_connector_tokens"
    
    if tokens_file.exists() and not use_dynamodb:
        # Use local file-based token storage
        console.print(f"[dim]Using local token storage: {tokens_file}[/dim]")
        try:
            import json
            
            # Load tokens from file
            with open(tokens_file, 'r') as f:
                tokens_data = json.load(f)
            
            if token_key not in tokens_data:
                console.print(f"[yellow]⚠️  No tokens found for {vendor}:{user_id}[/yellow]")
                console.print("   [dim]Tokens may have already been revoked or never existed.[/dim]")
                return
            
            # Remove the token
            del tokens_data[token_key]
            
            # Save back to file
            with open(tokens_file, 'w') as f:
                json.dump(tokens_data, f, indent=2)
            
            console.print("[green]✅ Tokens revoked successfully[/green]")
            console.print(f"   [dim]Removed from: {tokens_file}[/dim]")
            return
            
        except typer.Exit:
            # Re-raise typer.Exit exceptions (for early returns)
            raise
        except json.JSONDecodeError as e:
            console.print(f"[red]❌ Failed to parse tokens file: {e}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]❌ Error managing local tokens: {e}[/red]")
            if verbose:
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise typer.Exit(1)
    
    # Otherwise, try DynamoDB TokenStore
    try:
        from synheart_cloud_connector.tokens import TokenStore
        
        kms_key_id = os.getenv("KMS_KEY_ID")
        store = TokenStore(table_name=table_name, kms_key_id=kms_key_id)

        # Check if tokens exist before trying to revoke
        tokens = store.get_tokens(vendor_enum, user_id)
        if not tokens:
            console.print(f"[yellow]⚠️  No tokens found for {vendor}:{user_id}[/yellow]")
            console.print("   [dim]Tokens may have already been revoked or never existed.[/dim]")
            return

        # Revoke tokens
        store.revoke_tokens(vendor_enum, user_id)

        console.print("[green]✅ Tokens revoked successfully[/green]")
        return

    except ImportError as e:
        console.print(f"[red]❌ boto3 not available: {e}[/red]")
        console.print()
        console.print("[yellow]💡 For local development without DynamoDB:[/yellow]")
        console.print(f"   Tokens are stored in: [cyan]{tokens_file}[/cyan]")
        console.print(f"   You can manually edit this file or use the local token storage.")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        # Show more details if it's a TokenError or has underlying cause
        if hasattr(e, '__cause__') and e.__cause__:
            underlying_error = e.__cause__
            error_code = getattr(underlying_error, 'response', {}).get('Error', {}).get('Code', 'Unknown')
            error_message = getattr(underlying_error, 'response', {}).get('Error', {}).get('Message', str(underlying_error))
            console.print(f"   [dim]Error Code: {error_code}[/dim]")
            console.print(f"   [dim]Details: {error_message}[/dim]")
            # Common DynamoDB errors
            if error_code == "ResourceNotFoundException":
                console.print()
                console.print("[yellow]💡 The DynamoDB table doesn't exist.[/yellow]")
                console.print(f"   For local development, tokens are stored in: [cyan]{tokens_file}[/cyan]")
                console.print(f"   Try using file-based token management instead.")
                console.print()
                console.print(f"   Or set up DynamoDB: [cyan]DYNAMODB_TABLE=your_table_name[/cyan]")
            elif error_code == "ValidationException":
                console.print()
                console.print("[yellow]💡 Invalid table structure or key format.[/yellow]")
        if verbose:
            import traceback
            console.print()
            console.print("[dim]Full traceback:[/dim]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


# ============================================================================
# DEPLOY Commands (Coming Soon)
# ============================================================================

deploy_app = typer.Typer(help="Deployment commands (coming soon)")
app.add_typer(deploy_app, name="deploy")


@deploy_app.command()
def service(
    service_name: str = typer.Argument(..., help="Service name"),
    stage: str = typer.Argument("dev", help="Deployment stage"),
):
    """Deploy a service to production (coming soon)."""
    console.print()
    console.print("[bold yellow]🚧 Deployment Feature Coming Soon[/bold yellow]")
    console.print("━" * 60)
    console.print()
    console.print("[bold]We're focusing on local development first![/bold]")
    console.print()
    console.print("For now, use local development mode:")
    console.print(f"   [cyan]wear start dev --vendor {service_name.split('-')[0] if '-' in service_name else 'all'}[/cyan]")
    console.print()
    console.print("Production deployment will be available in a future release.")
    console.print()


@deploy_app.command()
def list_resources(
    service_name: str = typer.Argument(..., help="Service name"),
    stage: str = typer.Argument("dev", help="Deployment stage"),
):
    """List deployed resources (coming soon)."""
    console.print("[yellow]🚧 This feature is coming soon[/yellow]")
    console.print("Focus on local development for now: [cyan]wear start dev[/cyan]")


@deploy_app.command()
def logs(
    service_name: str = typer.Argument(..., help="Service name"),
    stage: str = typer.Argument("dev", help="Deployment stage"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
):
    """View service logs (coming soon)."""
    console.print("[yellow]🚧 This feature is coming soon[/yellow]")
    console.print("For local logs, use: [cyan]wear start dev --verbose[/cyan]")


@deploy_app.command()
def destroy(
    service_name: str = typer.Argument(..., help="Service name"),
    stage: str = typer.Argument("dev", help="Deployment stage"),
    force: bool = typer.Option(False, "--force", help="Destroy without confirmation"),
):
    """Destroy deployed resources (coming soon)."""
    console.print("[yellow]🚧 This feature is coming soon[/yellow]")
    console.print("For local development, just stop the server with Ctrl+C")


# ============================================================================
# VERSION Command
# ============================================================================

@app.command()
def version():
    """Show version information."""
    console.print("[bold]Synheart Wear CLI[/bold]")
    console.print("Version: [cyan]0.1.0[/cyan]")
    console.print()
    console.print(f"Repository: [dim]{REPO_ROOT}[/dim]")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    app()
