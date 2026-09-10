from pathlib import Path

from app.workspace.manager import WorkspaceManager


workspace_manager = WorkspaceManager()


def list_workspace_files(
    user_id: str,
    relative_directory: str = "",
) -> list[dict[str, str]]:
    """List files and directories inside a user's workspace.

    Args:
        user_id: Authenticated user's identifier.
        relative_directory: Directory relative to the user's workspace root.

    Returns:
        A list containing metadata about each immediate child.
    """

    directory = workspace_manager.resolve_user_path(
        user_id=user_id,
        relative_path=relative_directory,
    )

    if not directory.exists():
        raise FileNotFoundError(
            f"Directory does not exist: {relative_directory or '.'}"
        )

    if not directory.is_dir():
        raise NotADirectoryError(
            f"Path is not a directory: {relative_directory or '.'}"
        )

    entries: list[dict[str, str]] = []

    for entry in sorted(
        directory.iterdir(),
        key=lambda path: path.name.lower(),
    ):
        entries.append(
            {
                "name": entry.name,
                "path": entry.relative_to(
                    workspace_manager.user_root(user_id)
                ).as_posix(),
                "type": "directory" if entry.is_dir() else "file",
            }
        )

    return entries


def read_workspace_file(
    user_id: str,
    relative_path: str,
) -> str:
    """Read a UTF-8 text file from a user's isolated workspace.

    Args:
        user_id: Authenticated user's identifier.
        relative_path: Path relative to the user's workspace root.

    Returns:
        The text content of the file.
    """

    file_path = workspace_manager.resolve_user_path(
        user_id=user_id,
        relative_path=relative_path,
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"File does not exist: {relative_path}"
        )

    if not file_path.is_file():
        raise IsADirectoryError(
            f"Path is not a file: {relative_path}"
        )

    return file_path.read_text(
        encoding="utf-8",
    )


def write_workspace_file(
    user_id: str,
    relative_path: str,
    content: str,
) -> dict[str, str]:
    """Write UTF-8 text to a writable area of a user's workspace.

    Args:
        user_id: Authenticated user's identifier.
        relative_path: Path relative to the user's workspace root.
        content: Text content to write.

    Returns:
        Metadata describing the created file.
    """

    file_path = workspace_manager.validate_write_path(
        user_id=user_id,
        relative_path=relative_path,
    )

    user_root = workspace_manager.user_root(user_id)

    if not user_root.exists():
        workspace_manager.initialize_user_workspace(user_id)

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path.write_text(
        content,
        encoding="utf-8",
    )

    return {
        "path": file_path.relative_to(user_root).as_posix(),
        "status": "written",
    }