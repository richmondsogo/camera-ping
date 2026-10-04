from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import clock


def test_import_template(client: TestClient) -> None:
    response = client.get("/api/cameras/import/template")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "camera-template.csv" in response.headers.get("content-disposition", "")
    assert response.text == "camera_name,location,description,ip_address\r\n"


def test_export_empty_list(client: TestClient) -> None:
    response = client.get("/api/cameras/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=cameras-" in response.headers.get(
        "content-disposition", ""
    )
    # Check UTF-8 BOM
    assert response.content.startswith(b"\xef\xbb\xbf")
    text = response.content.decode("utf-8-sig")
    expected_header = (
        "camera_name,location,description,ip_address,"
        "status,last_checked,last_online\r\n"
    )
    assert text == expected_header


def test_export_with_cameras(client: TestClient) -> None:
    # Add a camera first
    create_res = client.post(
        "/api/cameras",
        json={
            "camera_name": "Gate A",
            "location": "Main Entrance",
            "description": "Gate overview",
            "ip_address": "192.0.2.10",
        },
    )
    assert create_res.status_code == 201

    response = client.get("/api/cameras/export")
    assert response.status_code == 200
    today_str = clock.utc_now().strftime("%Y-%m-%d")
    assert f"cameras-{today_str}.csv" in response.headers.get("content-disposition", "")

    text = response.content.decode("utf-8-sig")
    lines = text.split("\r\n")
    assert (
        lines[0]
        == "camera_name,location,description,ip_address,status,last_checked,last_online"
    )
    assert lines[1] == "Gate A,Main Entrance,Gate overview,192.0.2.10,unknown,,"
    # Ensure consecutive_failures and alert_sent are never in export
    assert "consecutive_failures" not in text
    assert "alert_sent_for_current_outage" not in text


def test_fixed_routes_not_captured_by_camera_id(client: TestClient) -> None:
    # Verify fixed paths are handled by their own handlers, not as /{camera_id}
    res_template = client.get("/api/cameras/import/template")
    assert res_template.status_code == 200

    res_export = client.get("/api/cameras/export")
    assert res_export.status_code == 200

    res_import = client.post("/api/cameras/import?dry_run=true", content=b"")
    assert res_import.status_code == 422
    assert res_import.json()["detail"][0]["msg"] == "The file has no cameras."


def test_happy_path_sample_cameras_30(client: TestClient) -> None:
    sample_path = (
        Path(__file__).resolve().parent.parent.parent
        / "shared"
        / "sample-cameras-30.csv"
    )
    assert sample_path.exists(), f"Missing sample file at {sample_path}"
    content = sample_path.read_bytes()

    # Dry run
    res_dry = client.post(
        "/api/cameras/import?dry_run=true",
        content=content,
        headers={"Content-Type": "text/csv"},
    )
    assert res_dry.status_code == 200
    dry_json = res_dry.json()
    assert dry_json["count"] == 30
    assert len(dry_json["preview"]) == 5
    assert dry_json["preview"][0]["camera_name"] == "Server Room Rack A"

    # Confirm DB is still empty
    res_list = client.get("/api/cameras")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 0

    # Real import
    res_import = client.post(
        "/api/cameras/import?dry_run=false",
        content=content,
        headers={"Content-Type": "text/csv"},
    )
    assert res_import.status_code == 201
    assert res_import.json() == {"imported": 30}

    # Verify DB now contains 30 cameras
    res_list2 = client.get("/api/cameras")
    assert len(res_list2.json()) == 30


def test_header_variants(client: TestClient) -> None:
    # Missing column
    res = client.post(
        "/api/cameras/import",
        content=b"camera_name,location,description\nCam1,Loc1,Desc1\n",
    )
    assert res.status_code == 422
    assert "Invalid CSV header" in res.json()["detail"][0]["msg"]

    # Extra column
    res = client.post(
        "/api/cameras/import",
        content=b"camera_name,location,description,ip_address,extra\nCam1,Loc1,Desc1,192.0.2.1,x\n",
    )
    assert res.status_code == 422
    assert "Invalid CSV header" in res.json()["detail"][0]["msg"]

    # Reordered column
    res = client.post(
        "/api/cameras/import",
        content=b"location,camera_name,description,ip_address\nLoc1,Cam1,Desc1,192.0.2.1\n",
    )
    assert res.status_code == 422
    assert "Invalid CSV header" in res.json()["detail"][0]["msg"]

    # Wrong case
    res = client.post(
        "/api/cameras/import",
        content=b"Camera_Name,Location,Description,IP_Address\nCam1,Loc1,Desc1,192.0.2.1\n",
    )
    assert res.status_code == 422
    assert "Invalid CSV header" in res.json()["detail"][0]["msg"]

    # Duplicated column
    res = client.post(
        "/api/cameras/import",
        content=b"camera_name,camera_name,description,ip_address\nCam1,Cam1,Desc1,192.0.2.1\n",
    )
    assert res.status_code == 422
    assert "Invalid CSV header" in res.json()["detail"][0]["msg"]


def test_header_semicolon_hint(client: TestClient) -> None:
    content = b"camera_name;location;description;ip_address\nCam1;Loc;Desc;192.0.2.1\n"
    res = client.post("/api/cameras/import", content=content)
    assert res.status_code == 422
    err_msg = res.json()["detail"][0]["msg"]
    assert (
        "This looks semicolon-separated. Save the file with commas as separators."
        in err_msg
    )


def test_bom_handling(client: TestClient) -> None:
    csv_bytes = (
        "\ufeffcamera_name,location,description,ip_address\r\n"
        "BOM Cam,HQ,Desc,192.0.2.55\r\n"
    ).encode("utf-8")
    res = client.post("/api/cameras/import?dry_run=false", content=csv_bytes)
    assert res.status_code == 201
    assert res.json() == {"imported": 1}


def test_crlf_and_lf_and_quoted_commas(client: TestClient) -> None:
    csv_text = (
        "camera_name,location,description,ip_address\r\n"
        '"Hallway, East","HQ, Bldg 1","A description, with, commas",192.0.2.20\r\n'
        "Standard Cam,Office,Single line desc,192.0.2.21\n"
    )
    res = client.post(
        "/api/cameras/import?dry_run=false", content=csv_text.encode("utf-8")
    )
    assert res.status_code == 201
    assert res.json() == {"imported": 2}


def test_non_utf8_bytes(client: TestClient) -> None:
    # cp1252 0xE9 (é)
    bad_bytes = (
        b"camera_name,location,description,ip_address\nCaf\xe9,HQ,Desc,192.0.2.1\n"
    )
    res = client.post("/api/cameras/import", content=bad_bytes)
    assert res.status_code == 422
    assert (
        res.json()["detail"][0]["msg"]
        == "The file isn't UTF-8. In Excel, use Save As and choose CSV UTF-8."
    )


def test_empty_file_and_header_only(client: TestClient) -> None:
    res_empty = client.post("/api/cameras/import", content=b"")
    assert res_empty.status_code == 422
    assert res_empty.json()["detail"][0]["msg"] == "The file has no cameras."

    res_header_only = client.post(
        "/api/cameras/import",
        content=b"camera_name,location,description,ip_address\r\n",
    )
    assert res_header_only.status_code == 422
    assert res_header_only.json()["detail"][0]["msg"] == "The file has no cameras."


def test_blank_lines_skipped(client: TestClient) -> None:
    csv_text = (
        "camera_name,location,description,ip_address\n\n"
        "Cam 1,Loc,Desc,192.0.2.1\n\n\n"
        "Cam 2,Loc,Desc,192.0.2.2\n\n"
    )
    res = client.post(
        "/api/cameras/import?dry_run=false", content=csv_text.encode("utf-8")
    )
    assert res.status_code == 201
    assert res.json() == {"imported": 2}


def test_short_and_long_rows(client: TestClient) -> None:
    csv_text = (
        "camera_name,location,description,ip_address\n"
        "Short Row,Loc,Desc\n"
        "Long Row,Loc,Desc,192.0.2.1,ExtraField\n"
    )
    res = client.post("/api/cameras/import", content=csv_text.encode("utf-8"))
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert len(detail) == 2
    assert detail[0]["loc"] == ["file", 2, "row"]
    assert detail[0]["msg"] == "Expected 4 fields, found 3."
    assert detail[1]["loc"] == ["file", 3, "row"]
    assert detail[1]["msg"] == "Expected 4 fields, found 5."


def test_every_row_level_rule(client: TestClient) -> None:
    # Verify each validation constraint rejects appropriately
    cases = [
        ("empty name", ",Loc,Desc,192.0.2.1", "camera_name"),
        ("empty loc", "Cam,,Desc,192.0.2.1", "location"),
        ("empty desc", "Cam,Loc,,192.0.2.1", "description"),
        ("empty ip", "Cam,Loc,Desc,", "ip_address"),
        ("too long name", f"{'a' * 101},Loc,Desc,192.0.2.1", "camera_name"),
        ("too long loc", f"Cam,{'a' * 101},Desc,192.0.2.1", "location"),
        ("too long desc", f"Cam,Loc,{'a' * 501},192.0.2.1", "description"),
        ("control char", "Cam\t1,Loc,Desc,192.0.2.1", "camera_name"),
        ("invalid ipv4", "Cam,Loc,Desc,999.1.1.1", "ip_address"),
        ("unspecified 0.0.0.0", "Cam,Loc,Desc,0.0.0.0", "ip_address"),
        ("multicast", "Cam,Loc,Desc,224.0.0.1", "ip_address"),
        ("broadcast", "Cam,Loc,Desc,255.255.255.255", "ip_address"),
        ("leading zero", "Cam,Loc,Desc,192.0.002.010", "ip_address"),
    ]

    for label, row, expected_col in cases:
        csv_text = f"camera_name,location,description,ip_address\n{row}\n"
        res = client.post("/api/cameras/import", content=csv_text.encode("utf-8"))
        assert res.status_code == 422, f"Expected 422 for {label}"
        detail = res.json()["detail"]
        assert any(d["loc"] == ["file", 2, expected_col] for d in detail), (
            f"Expected error on col {expected_col} for {label}: {detail}"
        )


def test_correct_line_numbers_with_blank_and_multiline_fields(
    client: TestClient,
) -> None:
    # Amendment 4: A blank line plus a quoted multi-line field before a bad row,
    # asserting the exact line number reported.
    csv_text = (
        "camera_name,location,description,ip_address\n"  # line 1
        "\n"  # line 2 (blank)
        '"Cam 1",Room 1,"Multi\n'  # line 3
        "line\n"  # line 4
        'desc",192.0.2.1\n'  # line 5
        "Cam 2,Room 2,Desc 2,bad_ip\n"  # line 6 (bad row)
    )
    res = client.post("/api/cameras/import", content=csv_text.encode("utf-8"))
    assert res.status_code == 422
    detail = res.json()["detail"]
    # The multiline record starts at line 3 (fails due to control chars)
    assert detail[0]["loc"] == ["file", 3, "description"]
    # The bad row after it reports line 6, counting blank and multiline rows
    assert detail[1]["loc"] == ["file", 6, "ip_address"]
    assert "valid IPv4" in detail[1]["msg"]


def test_duplicate_within_file_and_against_existing(client: TestClient) -> None:
    # Create an existing camera in DB
    client.post(
        "/api/cameras",
        json={
            "camera_name": "Existing",
            "location": "HQ",
            "description": "Desc",
            "ip_address": "192.0.2.1",
        },
    )

    csv_text = (
        "camera_name,location,description,ip_address\n"
        "Cam A,Loc,Desc,192.0.2.1\n"  # duplicate of existing DB camera
        "Cam B,Loc,Desc,192.0.2.2\n"  # first occurrence in file
        "Cam C,Loc,Desc,192.0.2.2\n"  # duplicate within file
    )
    res = client.post("/api/cameras/import", content=csv_text.encode("utf-8"))
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert len(detail) == 2
    # Row 2 against existing
    assert detail[0]["loc"] == ["file", 2, "ip_address"]
    assert detail[0]["msg"] == "A camera with this IP address already exists."
    assert detail[0]["type"] == "duplicate"
    # Row 4 duplicate of row 3
    assert detail[1]["loc"] == ["file", 4, "ip_address"]
    assert detail[1]["msg"] == "Same IP address as row 3."
    assert detail[1]["type"] == "duplicate"


def test_one_bad_row_in_30_means_zero_imported(client: TestClient) -> None:
    sample_path = (
        Path(__file__).resolve().parent.parent.parent
        / "shared"
        / "sample-cameras-30.csv"
    )
    lines = sample_path.read_text(encoding="utf-8").splitlines()
    # Corrupt line 15 (1-indexed line 16)
    lines[15] = "Corrupt Camera,Loc,Desc,999.999.999.999"
    bad_csv = "\n".join(lines) + "\n"

    res = client.post(
        "/api/cameras/import?dry_run=false", content=bad_csv.encode("utf-8")
    )
    assert res.status_code == 422
    # Verify 0 cameras committed
    res_list = client.get("/api/cameras")
    assert len(res_list.json()) == 0


def test_dry_run_writes_nothing_then_commit_works(client: TestClient) -> None:
    csv_text = (
        "camera_name,location,description,ip_address\n"
        "Cam 1,Room 1,Desc 1,192.0.2.10\n"
        "Cam 2,Room 2,Desc 2,192.0.2.11\n"
    )
    # Dry run
    res_dry = client.post(
        "/api/cameras/import?dry_run=true", content=csv_text.encode("utf-8")
    )
    assert res_dry.status_code == 200
    assert res_dry.json()["count"] == 2
    assert len(res_dry.json()["preview"]) == 2

    # Verify DB has 0
    assert len(client.get("/api/cameras").json()) == 0

    # Commit
    res_commit = client.post(
        "/api/cameras/import?dry_run=false", content=csv_text.encode("utf-8")
    )
    assert res_commit.status_code == 201
    assert res_commit.json()["imported"] == 2

    # Verify DB has 2
    assert len(client.get("/api/cameras").json()) == 2


def test_race_conflict_between_dry_run_and_commit(
    client: TestClient,
) -> None:
    from unittest.mock import patch

    from sqlalchemy.exc import IntegrityError

    csv_text = (
        "camera_name,location,description,ip_address\n"
        "Cam Race,Room 1,Desc 1,192.0.2.50\n"
    )
    # Dry run succeeds
    res_dry = client.post(
        "/api/cameras/import?dry_run=true", content=csv_text.encode("utf-8")
    )
    assert res_dry.status_code == 200

    # Simulate race condition: another transaction committed the same IP
    # immediately after validation, causing IntegrityError during db.commit()
    with patch.object(
        Session,
        "commit",
        side_effect=IntegrityError(
            "UNIQUE constraint failed: cameras.ip_address", None, Exception("UNIQUE")
        ),
    ):
        res_commit = client.post(
            "/api/cameras/import?dry_run=false", content=csv_text.encode("utf-8")
        )

    assert res_commit.status_code == 409
    detail = res_commit.json()["detail"]
    assert detail[0]["loc"] == ["file"]
    expected_race_msg = (
        "Another camera with one of these IP addresses "
        "was added in the meantime. Nothing was imported. Try again."
    )
    assert detail[0]["msg"] == expected_race_msg
    assert detail[0]["type"] == "duplicate"


def test_size_over_1_mib_and_stream_without_content_length(
    client: TestClient,
) -> None:
    # Amendment 5: read through request.stream() and stop at 1 MiB (413) without
    # buffering the whole body; do not trust Content-Length alone.
    # We yield chunks of 64 KiB totalling > 1 MiB (1024 * 1024 + 65536 bytes)
    def chunk_generator() -> Generator[bytes, None, None]:
        chunk = b"A" * 65536
        for _ in range(17):  # 17 * 64 KiB = 1,114,112 bytes > 1 MiB
            yield chunk

    # Sending a generator to TestClient streams without a pre-calculated Content-Length
    res = client.post("/api/cameras/import", content=chunk_generator())
    assert res.status_code == 413
    assert res.json()["detail"][0]["msg"] == "File size exceeds maximum limit of 1 MiB."
    assert res.json()["total_errors"] == 1


def test_over_1000_rows(client: TestClient) -> None:
    lines = ["camera_name,location,description,ip_address"]
    # 1001 rows
    for i in range(1001):
        # Generate valid IPv4 within documentation range
        b3 = (i // 250) + 1
        b4 = (i % 250) + 1
        lines.append(f"Cam {i},Loc,Desc,192.0.{b3}.{b4}")
    csv_text = "\n".join(lines) + "\n"

    res = client.post("/api/cameras/import", content=csv_text.encode("utf-8"))
    assert res.status_code == 422
    assert "exceeds the limit of 1000" in res.json()["detail"][0]["msg"]
    assert res.json()["detail"][0]["type"] == "too_many_rows"


def test_100_error_cap_with_total_errors(client: TestClient) -> None:
    lines = ["camera_name,location,description,ip_address"]
    for i in range(150):
        lines.append(f"Cam {i},Loc,Desc,invalid_ip_{i}")
    csv_text = "\n".join(lines) + "\n"

    res = client.post("/api/cameras/import", content=csv_text.encode("utf-8"))
    assert res.status_code == 422
    body = res.json()
    assert len(body["detail"]) == 100
    assert body["total_errors"] == 150


def test_nul_bytes(client: TestClient) -> None:
    csv_bytes = (
        b"camera_name,location,description,ip_address\nCam1\0,Loc,Desc,192.0.2.1\n"
    )
    res = client.post("/api/cameras/import", content=csv_bytes)
    assert res.status_code == 422
    assert res.json()["detail"][0]["msg"] == "The file contains NUL bytes."
