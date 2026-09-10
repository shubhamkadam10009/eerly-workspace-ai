from pathlib import Path

import pytest

from app.tools import filesystem


def test_list_workspace_files(tmp_path: Path) -> None:
    filesystem.workspace_manager.root = tmp_path

    user_root = filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    (user_root / "input" / "report.pdf").write_text(
        "test report",
        encoding="utf-8",
    )

    (user_root / "input" / "notes.txt").write_text(
        "test notes",
        encoding="utf-8",
    )

    results = filesystem.list_workspace_files(
        user_id="user_A",
        relative_directory="input",
    )

    assert results == [
        {
            "name": "notes.txt",
            "path": "input/notes.txt",
            "type": "file",
        },
        {
            "name": "report.pdf",
            "path": "input/report.pdf",
            "type": "file",
        },
    ]


def test_list_workspace_files_isolated_between_users(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    user_a_root = (
        filesystem.workspace_manager.initialize_user_workspace(
            "user_A"
        )
    )

    user_b_root = (
        filesystem.workspace_manager.initialize_user_workspace(
            "user_B"
        )
    )

    (user_a_root / "input" / "A-secret.txt").write_text(
        "User A secret",
        encoding="utf-8",
    )

    (user_b_root / "input" / "B-secret.txt").write_text(
        "User B secret",
        encoding="utf-8",
    )

    user_a_files = filesystem.list_workspace_files(
        user_id="user_A",
        relative_directory="input",
    )

    user_b_files = filesystem.list_workspace_files(
        user_id="user_B",
        relative_directory="input",
    )

    assert user_a_files == [
        {
            "name": "A-secret.txt",
            "path": "input/A-secret.txt",
            "type": "file",
        }
    ]

    assert user_b_files == [
        {
            "name": "B-secret.txt",
            "path": "input/B-secret.txt",
            "type": "file",
        }
    ]


@pytest.mark.parametrize(
    "relative_directory",
    [
        "../user_B/input",
        "../../user_B/input",
        "../../../",
        r"..\..\user_B\input",
    ],
)
def test_list_workspace_files_rejects_traversal(
    tmp_path: Path,
    relative_directory: str,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    filesystem.workspace_manager.initialize_user_workspace(
        "user_B"
    )

    with pytest.raises(
        ValueError,
        match="Path escapes user workspace",
    ):
        filesystem.list_workspace_files(
            user_id="user_A",
            relative_directory=relative_directory,
        )

def test_read_workspace_file(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    user_root = (
        filesystem.workspace_manager.initialize_user_workspace(
            "user_A"
        )
    )

    file_path = user_root / "input" / "report.txt"

    file_path.write_text(
        "This is a test report.",
        encoding="utf-8",
    )

    content = filesystem.read_workspace_file(
        user_id="user_A",
        relative_path="input/report.txt",
    )

    assert content == "This is a test report."

def test_read_workspace_file_not_found(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    with pytest.raises(
        FileNotFoundError,
        match="File does not exist",
    ):
        filesystem.read_workspace_file(
            user_id="user_A",
            relative_path="input/missing.txt",
        )

def test_read_workspace_file_rejects_directory(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    with pytest.raises(
        IsADirectoryError,
        match="Path is not a file",
    ):
        filesystem.read_workspace_file(
            user_id="user_A",
            relative_path="input",
        )

def test_read_workspace_file_isolated_between_users(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    user_a_root = (
        filesystem.workspace_manager.initialize_user_workspace(
            "user_A"
        )
    )

    user_b_root = (
        filesystem.workspace_manager.initialize_user_workspace(
            "user_B"
        )
    )

    (user_a_root / "input" / "A-secret.txt").write_text(
        "User A secret",
        encoding="utf-8",
    )

    (user_b_root / "input" / "B-secret.txt").write_text(
        "User B secret",
        encoding="utf-8",
    )

    user_a_content = filesystem.read_workspace_file(
        user_id="user_A",
        relative_path="input/A-secret.txt",
    )

    user_b_content = filesystem.read_workspace_file(
        user_id="user_B",
        relative_path="input/B-secret.txt",
    )

    assert user_a_content == "User A secret"
    assert user_b_content == "User B secret"

@pytest.mark.parametrize(
    "relative_path",
    [
        "../user_B/input/B-secret.txt",
        "../../user_B/input/B-secret.txt",
        r"..\..\user_B\input\B-secret.txt",
    ],
)
def test_read_workspace_file_rejects_cross_user_traversal(
    tmp_path: Path,
    relative_path: str,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    user_b_root = (
        filesystem.workspace_manager.initialize_user_workspace(
            "user_B"
        )
    )

    (user_b_root / "input" / "B-secret.txt").write_text(
        "User B secret",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Path escapes user workspace",
    ):
        filesystem.read_workspace_file(
            user_id="user_A",
            relative_path=relative_path,
        )

def test_write_workspace_file(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    result = filesystem.write_workspace_file(
        user_id="user_A",
        relative_path="working/report.txt",
        content="Generated report content",
    )

    assert result == {
        "path": "working/report.txt",
        "status": "written",
    }

    file_path = (
        tmp_path
        / "user_A"
        / "working"
        / "report.txt"
    )

    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == (
        "Generated report content"
    )

def test_write_workspace_file_creates_parent_directories(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    filesystem.write_workspace_file(
        user_id="user_A",
        relative_path="working/reports/final/report.md",
        content="# Final Report",
    )

    file_path = (
        tmp_path
        / "user_A"
        / "working"
        / "reports"
        / "final"
        / "report.md"
    )

    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == (
        "# Final Report"
    )

def test_write_workspace_file_overwrites_existing_file(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    filesystem.write_workspace_file(
        user_id="user_A",
        relative_path="working/report.txt",
        content="Version 1",
    )

    filesystem.write_workspace_file(
        user_id="user_A",
        relative_path="working/report.txt",
        content="Version 2",
    )

    file_path = (
        tmp_path
        / "user_A"
        / "working"
        / "report.txt"
    )

    assert file_path.read_text(encoding="utf-8") == "Version 2"

def test_write_workspace_file_rejects_cross_user_traversal(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    user_b_root = (
        filesystem.workspace_manager.initialize_user_workspace(
            "user_B"
        )
    )

    with pytest.raises(
        ValueError,
        match="Path escapes user workspace",
    ):
        filesystem.write_workspace_file(
            user_id="user_A",
            relative_path="../user_B/working/attack.txt",
            content="malicious content",
        )

    assert not (
        user_b_root
        / "working"
        / "attack.txt"
    ).exists()

@pytest.mark.parametrize(
    "relative_path",
    [
        "../../user_B/working/attack.txt",
        r"..\..\user_B\working\attack.txt",
        "../../../attack.txt",
    ],
)
def test_write_workspace_file_rejects_traversal(
    tmp_path: Path,
    relative_path: str,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    filesystem.workspace_manager.initialize_user_workspace(
        "user_B"
    )

    with pytest.raises(
        ValueError,
        match="Path escapes user workspace",
    ):
        filesystem.write_workspace_file(
            user_id="user_A",
            relative_path=relative_path,
            content="malicious content",
        )

def test_write_workspace_file_rejects_input_directory(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    input_file = (
        tmp_path
        / "user_A"
        / "input"
        / "original.txt"
    )

    input_file.write_text(
        "Original user content",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Writes are only allowed in working or delivered",
    ):
        filesystem.write_workspace_file(
            user_id="user_A",
            relative_path="input/original.txt",
            content="Attempted overwrite",
        )

    assert input_file.read_text(
        encoding="utf-8"
    ) == "Original user content"

def test_user_cannot_read_another_users_existing_file(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    user_a_root = (
        filesystem.workspace_manager.initialize_user_workspace(
            "user_A"
        )
    )

    user_b_root = (
        filesystem.workspace_manager.initialize_user_workspace(
            "user_B"
        )
    )

    secret_file = (
        user_b_root
        / "input"
        / "private.txt"
    )

    secret_file.write_text(
        "USER B PRIVATE DATA",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Path escapes user workspace",
    ):
        filesystem.read_workspace_file(
            user_id="user_A",
            relative_path="../user_B/input/private.txt",
        )

    assert secret_file.read_text(
        encoding="utf-8"
    ) == "USER B PRIVATE DATA"

    assert not (
        user_a_root
        / "input"
        / "private.txt"
    ).exists()


def test_user_cannot_write_into_another_users_existing_workspace(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    user_b_root = (
        filesystem.workspace_manager.initialize_user_workspace(
            "user_B"
        )
    )

    protected_file = (
        user_b_root
        / "working"
        / "important.txt"
    )

    protected_file.write_text(
        "USER B ORIGINAL DATA",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Path escapes user workspace",
    ):
        filesystem.write_workspace_file(
            user_id="user_A",
            relative_path="../user_B/working/important.txt",
            content="USER A ATTACK",
        )

    assert protected_file.read_text(
        encoding="utf-8"
    ) == "USER B ORIGINAL DATA"

def test_write_workspace_file_allows_delivered_directory(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    result = filesystem.write_workspace_file(
        user_id="user_A",
        relative_path="delivered/final-report.md",
        content="# Final Report",
    )

    assert result == {
        "path": "delivered/final-report.md",
        "status": "written",
    }

    file_path = (
        tmp_path
        / "user_A"
        / "delivered"
        / "final-report.md"
    )

    assert file_path.exists()
    assert file_path.read_text(
        encoding="utf-8"
    ) == "# Final Report"

def test_write_workspace_file_rejects_workspace_root(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    with pytest.raises(
        ValueError,
        match="Cannot write to workspace root",
    ):
        filesystem.write_workspace_file(
            user_id="user_A",
            relative_path="",
            content="Attempted root write",
        )

def test_write_workspace_file_allows_nested_working_path(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    result = filesystem.write_workspace_file(
        user_id="user_A",
        relative_path="working/reports/final/report.md",
        content="# Final Report",
    )

    assert result == {
        "path": "working/reports/final/report.md",
        "status": "written",
    }

    file_path = (
        tmp_path
        / "user_A"
        / "working"
        / "reports"
        / "final"
        / "report.md"
    )

    assert file_path.exists()
    assert file_path.read_text(
        encoding="utf-8"
    ) == "# Final Report"

def test_write_workspace_file_allows_nested_delivered_path(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    result = filesystem.write_workspace_file(
        user_id="user_A",
        relative_path="delivered/reports/final/report.md",
        content="# Final Delivered Report",
    )

    assert result == {
        "path": "delivered/reports/final/report.md",
        "status": "written",
    }

    file_path = (
        tmp_path
        / "user_A"
        / "delivered"
        / "reports"
        / "final"
        / "report.md"
    )

    assert file_path.exists()
    assert file_path.read_text(
        encoding="utf-8"
    ) == "# Final Delivered Report"

def test_write_workspace_file_allows_normalized_working_path(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    result = filesystem.write_workspace_file(
        user_id="user_A",
        relative_path="working/reports/../final/report.md",
        content="# Normalized Report",
    )

    assert result == {
        "path": "working/final/report.md",
        "status": "written",
    }

    file_path = (
        tmp_path
        / "user_A"
        / "working"
        / "final"
        / "report.md"
    )

    assert file_path.exists()
    assert file_path.read_text(
        encoding="utf-8"
    ) == "# Normalized Report"

def test_write_workspace_file_rejects_normalized_escape(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )

    filesystem.workspace_manager.initialize_user_workspace(
        "user_B"
    )

    with pytest.raises(
        ValueError,
        match="Path escapes user workspace",
    ):
        filesystem.write_workspace_file(
            user_id="user_A",
            relative_path="working/../../user_B/working/attack.txt",
            content="malicious content",
        )

def test_write_workspace_file_rejects_new_input_file(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    user_root = (
        filesystem.workspace_manager.initialize_user_workspace(
            "user_A"
        )
    )

    input_file = (
        user_root
        / "input"
        / "generated.txt"
    )

    with pytest.raises(
        ValueError,
        match="Writes are only allowed in working or delivered",
    ):
        filesystem.write_workspace_file(
            user_id="user_A",
            relative_path="input/generated.txt",
            content="This must not be written",
        )

    assert not input_file.exists()

@pytest.mark.parametrize(
    "user_id",
    [
        "",
        ".",
        "..",
        "../user_B",
        "user/A",
        r"user\B",
        r"C:\secret",
    ],
)
def test_filesystem_tools_reject_invalid_user_id(
    tmp_path: Path,
    user_id: str,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    with pytest.raises(ValueError):
        filesystem.list_workspace_files(
            user_id=user_id,
        )
def test_filesystem_tools_reject_absolute_cross_user_path(
    tmp_path: Path,
) -> None:
    filesystem.workspace_manager.root = tmp_path

    user_a_root = filesystem.workspace_manager.initialize_user_workspace(
        "user_A"
    )
    user_b_root = filesystem.workspace_manager.initialize_user_workspace(
        "user_B"
    )

    secret_file = user_b_root / "input" / "private.txt"
    secret_file.write_text(
        "USER B PRIVATE DATA",
        encoding="utf-8",
    )

    absolute_cross_user_path = str(secret_file)

    with pytest.raises(ValueError):
        filesystem.read_workspace_file(
            user_id="user_A",
            relative_path=absolute_cross_user_path,
        )

    assert secret_file.read_text(encoding="utf-8") == "USER B PRIVATE DATA"
    assert not (
        user_a_root / "input" / "private.txt"
    ).exists()
