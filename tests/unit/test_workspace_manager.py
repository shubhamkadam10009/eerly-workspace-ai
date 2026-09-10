from pathlib import Path

import pytest

from app.workspace.manager import WorkspaceManager


def test_valid_user_id() -> None:
    manager = WorkspaceManager()

    assert manager.validate_user_id("user_A") == "user_A"
    assert manager.validate_user_id("user-123") == "user-123"
    assert manager.validate_user_id("alice123") == "alice123"
    assert manager.validate_user_id("USER_123") == "USER_123"


@pytest.mark.parametrize(
    "user_id",
    [
        "",
        ".",
        "..",
        "../user_B",
        "../../secret",
        "user/A",
        r"user\B",
        r"C:\secret",
    ],
)
def test_invalid_user_id(user_id: str) -> None:
    manager = WorkspaceManager()

    with pytest.raises(ValueError):
        manager.validate_user_id(user_id)


def test_user_root(tmp_path: Path) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    result = manager.user_root("user_A")

    assert result == tmp_path / "user_A"


def test_resolve_valid_relative_path(tmp_path: Path) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    resolved = manager.resolve_user_path(
        "user_A",
        "input/report.pdf",
    )

    expected = (
        tmp_path / "user_A" / "input" / "report.pdf"
    ).resolve()

    assert resolved == expected


def test_resolve_nested_relative_path(tmp_path: Path) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    resolved = manager.resolve_user_path(
        "user_A",
        "working/reports/final/report.pdf",
    )

    expected = (
        tmp_path
        / "user_A"
        / "working"
        / "reports"
        / "final"
        / "report.pdf"
    ).resolve()

    assert resolved == expected


def test_resolve_normalizes_dot_segments(
    tmp_path: Path,
) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    resolved = manager.resolve_user_path(
        "user_A",
        "input/../working/report.txt",
    )

    expected = (
        tmp_path / "user_A" / "working" / "report.txt"
    ).resolve()

    assert resolved == expected


@pytest.mark.parametrize(
    "relative_path",
    [
        "../../user_B/secret.txt",
        "../secret.txt",
        "../../../etc/passwd",
        r"..\..\user_B\secret.txt",
        r"C:\secret.txt",
        "/etc/passwd",
    ],
)
def test_resolve_rejects_workspace_escape(
    tmp_path: Path,
    relative_path: str,
) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    with pytest.raises(
        ValueError,
        match="Path escapes user workspace",
    ):
        manager.resolve_user_path(
            "user_A",
            relative_path,
        )


def test_initialize_user_workspace(
    tmp_path: Path,
) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    user_root = manager.initialize_user_workspace("user_A")

    assert user_root == tmp_path / "user_A"

    assert (user_root / "input").is_dir()
    assert (user_root / "working").is_dir()
    assert (user_root / "delivered").is_dir()


def test_initialize_user_workspace_is_idempotent(
    tmp_path: Path,
) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    first = manager.initialize_user_workspace("user_A")
    second = manager.initialize_user_workspace("user_A")

    assert first == second

    assert (user_root := manager.user_root("user_A")).is_dir()
    assert (user_root / "input").is_dir()
    assert (user_root / "working").is_dir()
    assert (user_root / "delivered").is_dir()

def test_resolve_rejects_symlink_escape(
    tmp_path: Path,
) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    user_a = tmp_path / "user_A"
    user_b = tmp_path / "user_B"

    user_a_input = user_a / "input"
    user_b.mkdir(parents=True)
    user_a_input.mkdir(parents=True)

    secret_file = user_b / "secret.txt"
    secret_file.write_text(
        "user_B secret",
        encoding="utf-8",
    )

    symlink = user_a_input / "escape"

    try:
        symlink.symlink_to(
            user_b,
            target_is_directory=True,
        )
    except OSError as exc:
        pytest.skip(f"Symlink creation is unavailable: {exc}")

    with pytest.raises(
        ValueError,
        match="Path escapes user workspace",
    ):
        manager.resolve_user_path(
            "user_A",
            "input/escape/secret.txt",
        )

def test_validate_write_path_allows_working_directory(
    tmp_path: Path,
) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    manager.initialize_user_workspace("user_A")

    result = manager.validate_write_path(
        user_id="user_A",
        relative_path="working/report.txt",
    )

    expected = (
        tmp_path
        / "user_A"
        / "working"
        / "report.txt"
    ).resolve()

    assert result == expected


def test_validate_write_path_allows_delivered_directory(
    tmp_path: Path,
) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    manager.initialize_user_workspace("user_A")

    result = manager.validate_write_path(
        user_id="user_A",
        relative_path="delivered/final-report.md",
    )

    expected = (
        tmp_path
        / "user_A"
        / "delivered"
        / "final-report.md"
    ).resolve()

    assert result == expected


def test_validate_write_path_rejects_input_directory(
    tmp_path: Path,
) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    manager.initialize_user_workspace("user_A")

    with pytest.raises(
        ValueError,
        match="Writes are only allowed in working or delivered",
    ):
        manager.validate_write_path(
            user_id="user_A",
            relative_path="input/original.txt",
        )


def test_validate_write_path_rejects_workspace_root(
    tmp_path: Path,
) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    manager.initialize_user_workspace("user_A")

    with pytest.raises(
        ValueError,
        match="Cannot write to workspace root",
    ):
        manager.validate_write_path(
            user_id="user_A",
            relative_path="",
        )


@pytest.mark.parametrize(
    "relative_path",
    [
        "../user_B/working/attack.txt",
        "../../user_B/working/attack.txt",
        "../../../attack.txt",
        r"..\..\user_B\working\attack.txt",
    ],
)
def test_validate_write_path_rejects_workspace_escape(
    tmp_path: Path,
    relative_path: str,
) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    manager.initialize_user_workspace("user_A")
    manager.initialize_user_workspace("user_B")

    with pytest.raises(
        ValueError,
        match="Path escapes user workspace",
    ):
        manager.validate_write_path(
            user_id="user_A",
            relative_path=relative_path,
        )

def test_user_workspaces_are_physically_separate(
    tmp_path: Path,
) -> None:
    manager = WorkspaceManager()
    manager.root = tmp_path

    user_a_root = manager.initialize_user_workspace("user_A")
    user_b_root = manager.initialize_user_workspace("user_B")

    assert user_a_root != user_b_root
    assert user_a_root == tmp_path / "user_A"
    assert user_b_root == tmp_path / "user_B"

    assert user_a_root.is_dir()
    assert user_b_root.is_dir()

    assert user_a_root / "input" != user_b_root / "input"