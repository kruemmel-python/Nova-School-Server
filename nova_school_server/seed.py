from __future__ import annotations

from .auth import AuthService
from .code_runner import DEFAULT_CONTAINER_IMAGES
from .database import SchoolRepository
from .docs_catalog import DocumentationCatalog
from .workspace import WorkspaceManager, slugify


def bootstrap_application(repository: SchoolRepository, auth_service: AuthService, docs_catalog: DocumentationCatalog, workspace_manager: WorkspaceManager) -> dict[str, object]:
    docs_catalog.ensure_seed_docs()

    repository.put_setting("school_name", repository.get_setting("school_name", "Nova School Server"))
    repository.put_setting("server_public_host", repository.get_setting("server_public_host", ""))
    repository.put_setting("web_proxy_url", repository.get_setting("web_proxy_url", ""))
    repository.put_setting("web_proxy_no_proxy", repository.get_setting("web_proxy_no_proxy", ""))
    repository.put_setting("web_proxy_required", repository.get_setting("web_proxy_required", False))
    repository.put_setting("lmstudio_base_url", repository.get_setting("lmstudio_base_url", "http://127.0.0.1:1234/v1"))
    repository.put_setting("lmstudio_model", repository.get_setting("lmstudio_model", ""))
    repository.put_setting("runner_backend", repository.get_setting("runner_backend", "container"))
    repository.put_setting("unsafe_process_backend_enabled", repository.get_setting("unsafe_process_backend_enabled", False))
    repository.put_setting("playground_dispatch_mode", repository.get_setting("playground_dispatch_mode", "worker"))
    repository.put_setting("container_runtime", repository.get_setting("container_runtime", "docker"))
    repository.put_setting("container_oci_runtime", repository.get_setting("container_oci_runtime", ""))
    repository.put_setting("container_memory_limit", repository.get_setting("container_memory_limit", "512m"))
    repository.put_setting("container_cpu_limit", repository.get_setting("container_cpu_limit", "1.5"))
    repository.put_setting("container_pids_limit", repository.get_setting("container_pids_limit", "128"))
    repository.put_setting("container_file_size_limit_kb", repository.get_setting("container_file_size_limit_kb", 65536))
    repository.put_setting("container_nofile_limit", repository.get_setting("container_nofile_limit", 256))
    repository.put_setting("container_tmpfs_limit", repository.get_setting("container_tmpfs_limit", "64m"))
    repository.put_setting("container_seccomp_enabled", repository.get_setting("container_seccomp_enabled", True))
    repository.put_setting("container_seccomp_profile", repository.get_setting("container_seccomp_profile", ""))
    repository.put_setting("container_image_python", repository.get_setting("container_image_python", DEFAULT_CONTAINER_IMAGES["python"]))
    repository.put_setting("container_image_node", repository.get_setting("container_image_node", DEFAULT_CONTAINER_IMAGES["node"]))
    repository.put_setting("container_image_cpp", repository.get_setting("container_image_cpp", DEFAULT_CONTAINER_IMAGES["cpp"]))
    repository.put_setting("container_image_java", repository.get_setting("container_image_java", DEFAULT_CONTAINER_IMAGES["java"]))
    repository.put_setting("container_image_rust", repository.get_setting("container_image_rust", DEFAULT_CONTAINER_IMAGES["rust"]))
    repository.put_setting("scheduler_max_concurrent_global", repository.get_setting("scheduler_max_concurrent_global", 4))
    repository.put_setting("scheduler_max_concurrent_student", repository.get_setting("scheduler_max_concurrent_student", 1))
    repository.put_setting("scheduler_max_concurrent_teacher", repository.get_setting("scheduler_max_concurrent_teacher", 2))
    repository.put_setting("scheduler_max_concurrent_admin", repository.get_setting("scheduler_max_concurrent_admin", 3))

    users = [
        auth_service.ensure_user("admin", "NovaSchool!admin", "admin", "Server Admin"),
        auth_service.ensure_user("teacher", "NovaSchool!teacher", "teacher", "Lehrkraft"),
        auth_service.ensure_user("student", "NovaSchool!student", "student", "Schueler Demo"),
    ]

    if repository.get_group("class-1a") is None:
        repository.create_group("class-1a", "Klasse 1A", description="Demo-Klasse fuer den Nova School Server", permissions={"workspace.group": True, "chat.use": True, "docs.read": True})
    repository.add_membership("student", "class-1a")

    for user in users:
        workspace_manager.ensure_profile_folder("user", str(user["username"]))
    workspace_manager.ensure_profile_folder("group", "class-1a")

    if repository.find_project_by_owner_and_slug("user", "student", slugify("python-labor")) is None:
        project = repository.create_project(
            owner_type="user",
            owner_key="student",
            name="Python Labor",
            slug=slugify("python-labor"),
            template="python",
            runtime="python",
            main_file="main.py",
            description="Persoenliches Demo-Projekt fuer Python.",
            created_by="admin",
        )
        workspace_manager.materialize_project(project)

    if repository.find_project_by_owner_and_slug("group", "class-1a", slugify("web-labor")) is None:
        project = repository.create_project(
            owner_type="group",
            owner_key="class-1a",
            name="Web Labor",
            slug=slugify("web-labor"),
            template="frontend-lab",
            runtime="html",
            main_file="index.html",
            description="Gemeinsames Frontend-Projekt fuer die Klasse.",
            created_by="teacher",
        )
        workspace_manager.materialize_project(project)

    if repository.find_project_by_owner_and_slug("user", "teacher", slugify("distributed-playground")) is None:
        project = repository.create_project(
            owner_type="user",
            owner_key="teacher",
            name="Distributed Playground",
            slug=slugify("distributed-playground"),
            template="distributed-system",
            runtime="python",
            main_file="services/coordinator.py",
            description="Demo-Projekt fuer Worker-Orchestrierung, Trust Policies und verteilte Services.",
            created_by="admin",
        )
        workspace_manager.materialize_project(project)

    return {
        "seed_users": [
            {"username": "admin", "password": "NovaSchool!admin"},
            {"username": "teacher", "password": "NovaSchool!teacher"},
            {"username": "student", "password": "NovaSchool!student"},
        ],
        "seed_group": "class-1a",
    }
