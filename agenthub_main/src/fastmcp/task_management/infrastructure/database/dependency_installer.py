"""
Dependency Installer

Automatically installs missing dependencies required for PostgreSQL testing.
"""

import importlib.util
import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)


def install_missing_dependencies():
    """
    Install missing dependencies required for testing.

    This function checks for and installs:
    - docker: Required for some integration tests
    - psycopg2-binary: Required for PostgreSQL connections
    """
    dependencies_installed = []

    try:
        # Check for docker module
        if importlib.util.find_spec("docker") is not None:
            logger.info("'docker' module already available")
        else:
            logger.info("Installing missing 'docker' module...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "docker"],
                capture_output=True,
                text=True,
            )
            dependencies_installed.append("docker")
            logger.info("Successfully installed 'docker' module")

        # Check for psycopg2
        if importlib.util.find_spec("psycopg2") is not None:
            logger.info("'psycopg2' module already available")
        else:
            logger.info("Installing missing 'psycopg2-binary' module...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "psycopg2-binary"],
                capture_output=True,
                text=True,
            )
            dependencies_installed.append("psycopg2-binary")
            logger.info("Successfully installed 'psycopg2-binary' module")

        # Check for pytest if we're in a test context
        if "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ:
            if importlib.util.find_spec("pytest") is not None:
                logger.info("'pytest' module already available")
            else:
                logger.info("Installing missing 'pytest' module...")
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "pytest"],
                    capture_output=True,
                    text=True,
                )
                dependencies_installed.append("pytest")
                logger.info("Successfully installed 'pytest' module")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        raise RuntimeError(f"Dependency installation failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during dependency installation: {e}")
        raise

    if dependencies_installed:
        logger.info(
            f"Successfully installed dependencies: {', '.join(dependencies_installed)}"
        )
    else:
        logger.info("All required dependencies are already available")

    return dependencies_installed


def check_dependency_availability():
    """
    Check which dependencies are available without installing them.

    Returns:
        dict: Dictionary with dependency name as key and availability as value
    """
    availability = {}

    # Check docker
    availability["docker"] = importlib.util.find_spec("docker") is not None

    # Check psycopg2
    availability["psycopg2"] = importlib.util.find_spec("psycopg2") is not None

    # Check pytest
    availability["pytest"] = importlib.util.find_spec("pytest") is not None

    return availability


if __name__ == "__main__":
    import os

    print("Dependency Installer")
    print("=" * 30)

    # Check current availability
    print("Current dependency availability:")
    availability = check_dependency_availability()
    for dep, available in availability.items():
        status = "✅" if available else "❌"
        print(f"  {status} {dep}")

    # Install missing dependencies
    missing = [dep for dep, available in availability.items() if not available]
    if missing:
        print(f"\nInstalling missing dependencies: {', '.join(missing)}")
        try:
            installed = install_missing_dependencies()
            print(f"✅ Successfully installed: {', '.join(installed)}")
        except Exception as e:
            print(f"❌ Installation failed: {e}")
    else:
        print("\n✅ All dependencies are already available")
