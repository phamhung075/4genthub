#!/usr/bin/env python3
"""
4genthub Docker Menu Interface
Interactive menu system for Docker CLI operations
"""

import os
import sys
import subprocess
from typing import List, Tuple, Callable
from enum import Enum

try:
    import questionary
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "questionary", "rich"])
    import questionary
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown

console = Console()

class MenuStyle:
    """Custom styling for questionary"""
    def __init__(self):
        self.style = questionary.Style([
            ('qmark', 'fg:#673ab7 bold'),
            ('question', 'bold'),
            ('answer', 'fg:#f44336 bold'),
            ('pointer', 'fg:#673ab7 bold'),
            ('highlighted', 'fg:#673ab7 bold'),
            ('selected', 'fg:#cc5454'),
            ('separator', 'fg:#cc5454'),
            ('instruction', '')
        ])

menu_style = MenuStyle()

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def show_header():
    """Display the application header"""
    clear_screen()
    console.print(Panel.fit(
        "[bold cyan]4genthub Docker Management System[/bold cyan]\n"
        "[dim]PostgreSQL-First Architecture v2.0[/dim]",
        border_style="cyan"
    ))
    console.print()

def run_command(cmd: str, interactive: bool = False) -> Tuple[bool, str]:
    """Execute a docker-cli.sh command"""
    full_cmd = f"./docker-cli.sh {cmd}"
    console.print(f"[dim]Running: {full_cmd}[/dim]")
    
    try:
        if interactive:
            # For interactive commands like shell or logs
            subprocess.call(full_cmd, shell=True)
            return True, ""
        else:
            # For non-interactive commands
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                console.print("[green]✓ Success[/green]")
                if result.stdout:
                    console.print(result.stdout)
                return True, result.stdout
            else:
                console.print(f"[red]✗ Failed[/red]")
                if result.stderr:
                    console.print(f"[red]{result.stderr}[/red]")
                return False, result.stderr
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return False, str(e)

def quick_actions_menu():
    """Quick actions submenu"""
    while True:
        show_header()
        console.print("[bold magenta]🚀 Quick Actions[/bold magenta]\n")
        
        choices = [
            "▶️  Start all services",
            "⏹️  Stop all services", 
            "🔄 Restart all services",
            "📊 Show status",
            "📜 View logs (all services)",
            "🚀 Run dev setup workflow",
            "🔥 Start with hot reload",
            "↩️  Back to main menu"
        ]
        
        action = questionary.select(
            "Select an action:",
            choices=choices,
            style=menu_style.style
        ).ask()
        
        if "Back to main menu" in action:
            break
        elif "Start all services" in action:
            run_command("start")
        elif "Stop all services" in action:
            run_command("stop")
        elif "Restart all services" in action:
            run_command("restart")
        elif "Show status" in action:
            run_command("status")
        elif "View logs" in action:
            run_command("logs", interactive=True)
        elif "dev setup workflow" in action:
            run_command("workflow dev-setup")
        elif "hot reload" in action:
            run_command("start")
            console.print("\n[green]✅ Services started with hot reload[/green]")
            console.print("Backend: http://localhost:8000")
            console.print("Frontend: http://localhost:3000")
        
        if "Back to main menu" not in action:
            input("\nPress Enter to continue...")

def database_menu():
    """Database operations submenu"""
    while True:
        show_header()
        console.print("[bold magenta]🗄️  Database Operations[/bold magenta]\n")
        
        choices = [
            "📊 Database status",
            "🔧 Initialize database",
            "📈 Run migrations",
            "💾 Backup database",
            "📥 Restore database",
            "🖥️  Database shell (psql)",
            "🌱 Seed development data",
            "⚠️  Reset database (WARNING)",
            "↩️  Back to main menu"
        ]
        
        action = questionary.select(
            "Select an operation:",
            choices=choices,
            style=menu_style.style
        ).ask()
        
        if "Back to main menu" in action:
            break
        elif "Database status" in action:
            run_command("db status")
        elif "Initialize database" in action:
            run_command("db init")
        elif "Run migrations" in action:
            run_command("db migrate")
        elif "Backup database" in action:
            run_command("db backup")
        elif "Restore database" in action:
            # Show available backups first
            run_command("backup list")
            backup_file = questionary.text(
                "Enter backup file name (or leave empty to cancel):",
                style=menu_style.style
            ).ask()
            if backup_file:
                run_command(f"db restore {backup_file}")
        elif "Database shell" in action:
            run_command("db shell", interactive=True)
        elif "Seed development" in action:
            run_command("dev seed")
        elif "Reset database" in action:
            console.print("[bold red]⚠️  WARNING: This will DELETE ALL DATA![/bold red]")
            confirm = questionary.confirm(
                "Are you sure you want to reset the database?",
                default=False,
                style=menu_style.style
            ).ask()
            if confirm:
                run_command("db reset")
        
        if "Back to main menu" not in action:
            input("\nPress Enter to continue...")

def development_menu():
    """Development tools submenu"""
    while True:
        show_header()
        console.print("[bold magenta]🔧 Development Tools[/bold magenta]\n")
        
        choices = [
            "🔧 Setup development environment",
            "🔄 Reset development data",
            "🌱 Seed sample data",
            "🏗️  Build images",
            "🧪 Run tests",
            "🖥️  Shell access",
            "📜 View logs",
            "↩️  Back to main menu"
        ]
        
        action = questionary.select(
            "Select a tool:",
            choices=choices,
            style=menu_style.style
        ).ask()
        
        if "Back to main menu" in action:
            break
        elif "Setup development" in action:
            run_command("dev setup")
        elif "Reset development" in action:
            run_command("dev reset")
        elif "Seed sample" in action:
            run_command("dev seed")
        elif "Build images" in action:
            service = questionary.select(
                "Select service to build:",
                choices=["backend", "frontend", "all"],
                style=menu_style.style
            ).ask()
            run_command(f"build {service}")
        elif "Run tests" in action:
            test_type = questionary.select(
                "Select test type:",
                choices=["unit", "integration", "e2e", "all"],
                style=menu_style.style
            ).ask()
            run_command(f"test {test_type}")
        elif "Shell access" in action:
            service = questionary.select(
                "Select service:",
                choices=["backend", "frontend", "postgres", "redis"],
                style=menu_style.style
            ).ask()
            run_command(f"shell {service}", interactive=True)
        elif "View logs" in action:
            service = questionary.select(
                "Select service:",
                choices=["backend", "frontend", "postgres", "redis", "all"],
                style=menu_style.style
            ).ask()
            if service == "all":
                run_command("logs", interactive=True)
            else:
                run_command(f"logs {service}", interactive=True)
        
        if "Back to main menu" not in action:
            input("\nPress Enter to continue...")

def deployment_menu():
    """Deployment and scaling submenu"""
    while True:
        show_header()
        console.print("[bold magenta]📦 Deployment & Scaling[/bold magenta]\n")
        
        choices = [
            "🚀 Deploy to environment",
            "📈 Scale service",
            "🏥 Health check",
            "📊 Monitoring dashboard",
            "📋 Production deploy workflow",
            "↩️  Back to main menu"
        ]
        
        action = questionary.select(
            "Select an option:",
            choices=choices,
            style=menu_style.style
        ).ask()
        
        if "Back to main menu" in action:
            break
        elif "Deploy to environment" in action:
            env = questionary.select(
                "Select environment:",
                choices=["staging", "production"],
                style=menu_style.style
            ).ask()
            run_command(f"deploy {env}")
        elif "Scale service" in action:
            service = questionary.select(
                "Select service to scale:",
                choices=["backend", "frontend"],
                style=menu_style.style
            ).ask()
            replicas = questionary.text(
                "Number of replicas:",
                validate=lambda x: x.isdigit() and 0 <= int(x) <= 10,
                style=menu_style.style
            ).ask()
            run_command(f"scale {service} {replicas}")
        elif "Health check" in action:
            run_command("health")
        elif "Monitoring dashboard" in action:
            run_command("monitor", interactive=True)
        elif "Production deploy" in action:
            run_command("workflow prod-deploy")
        
        if "Back to main menu" not in action:
            input("\nPress Enter to continue...")

def maintenance_menu():
    """Backup and maintenance submenu"""
    while True:
        show_header()
        console.print("[bold magenta]💾 Backup & Maintenance[/bold magenta]\n")
        
        choices = [
            "💾 Create backup",
            "📥 Restore backup",
            "📋 List backups",
            "🧹 Cleanup unused resources",
            "🔄 Update system",
            "📦 Emergency backup",
            "↩️  Back to main menu"
        ]
        
        action = questionary.select(
            "Select an option:",
            choices=choices,
            style=menu_style.style
        ).ask()
        
        if "Back to main menu" in action:
            break
        elif "Create backup" in action:
            backup_type = questionary.select(
                "Select backup type:",
                choices=["full", "database", "volumes", "configs"],
                style=menu_style.style
            ).ask()
            run_command(f"backup create {backup_type}")
        elif "Restore backup" in action:
            run_command("backup list")
            backup_file = questionary.text(
                "Enter backup file name:",
                style=menu_style.style
            ).ask()
            if backup_file:
                run_command(f"backup restore {backup_file}")
        elif "List backups" in action:
            run_command("backup list")
        elif "Cleanup unused" in action:
            run_command("cleanup")
        elif "Update system" in action:
            run_command("update")
        elif "Emergency backup" in action:
            run_command("emergency-backup")
        
        if "Back to main menu" not in action:
            input("\nPress Enter to continue...")

def main_menu():
    """Main menu loop"""
    while True:
        show_header()
        
        # Create a nice table for the main menu
        table = Table(title="Main Menu", show_header=False, box=None)
        table.add_column("Option", style="cyan", width=50)
        
        menu_items = [
            "🚀 Quick Actions",
            "🗄️  Database Operations",
            "🔧 Development Tools",
            "📦 Deployment & Scaling",
            "💾 Backup & Maintenance",
            "⚙️  Configuration",
            "🔍 Troubleshooting",
            "📊 Monitoring Dashboard",
            "📚 Help & Documentation",
            "🚪 Exit"
        ]
        
        for item in menu_items:
            table.add_row(item)
        
        console.print(table)
        console.print()
        
        choice = questionary.select(
            "What would you like to do?",
            choices=menu_items,
            style=menu_style.style
        ).ask()
        
        if "Quick Actions" in choice:
            quick_actions_menu()
        elif "Database Operations" in choice:
            database_menu()
        elif "Development Tools" in choice:
            development_menu()
        elif "Deployment & Scaling" in choice:
            deployment_menu()
        elif "Backup & Maintenance" in choice:
            maintenance_menu()
        elif "Configuration" in choice:
            # Simple config options
            config_action = questionary.select(
                "Configuration options:",
                choices=[
                    "Show configuration",
                    "Validate configuration",
                    "Switch environment",
                    "Fix permissions",
                    "Back"
                ],
                style=menu_style.style
            ).ask()
            
            if "Show configuration" in config_action:
                run_command("config show")
            elif "Validate configuration" in config_action:
                run_command("config validate")
            elif "Switch environment" in config_action:
                env = questionary.select(
                    "Select environment:",
                    choices=["dev", "staging", "production"],
                    style=menu_style.style
                ).ask()
                run_command(f"env {env}")
            elif "Fix permissions" in config_action:
                run_command("fix-permissions")
            
            if "Back" not in config_action:
                input("\nPress Enter to continue...")
                
        elif "Troubleshooting" in choice:
            trouble_action = questionary.select(
                "Troubleshooting options:",
                choices=[
                    "Run diagnostics",
                    "Generate support bundle",
                    "Comprehensive health check",
                    "Back"
                ],
                style=menu_style.style
            ).ask()
            
            if "Run diagnostics" in trouble_action:
                run_command("diagnose")
            elif "Generate support" in trouble_action:
                run_command("support-bundle")
            elif "Comprehensive health" in trouble_action:
                run_command("workflow health-check")
            
            if "Back" not in trouble_action:
                input("\nPress Enter to continue...")
                
        elif "Monitoring Dashboard" in choice:
            run_command("monitor", interactive=True)
        elif "Help & Documentation" in choice:
            run_command("help")
            input("\nPress Enter to continue...")
        elif "Exit" in choice:
            console.print("\n[green]👋 Goodbye![/green]\n")
            sys.exit(0)

def main():
    """Entry point"""
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()