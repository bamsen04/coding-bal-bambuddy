"""Print requests: queue:request users queue staged items that wait for queue:approve.

A user who may only request prints can put a library file in the queue, aimed
at a printer or model, but cannot get it printed: the item is always staged and
flagged ``requires_approval``, and only a queue:approve holder can start, edit
or reject it -- the requester included, and an operator with queue:update_all
but no queue:approve excluded.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.models.library import LibraryFile
from backend.app.models.print_queue import PrintQueueItem

REQUESTER_PERMS = [
    "queue:request",
    "queue:read_own",
    "queue:update_own",
    "queue:delete_own",
    "library:read_all",
]
APPROVER_PERMS = ["queue:approve", "queue:read_all", "queue:update_own", "queue:delete_own"]
OPERATOR_PERMS = ["queue:create", "queue:read_all", "queue:update_all", "queue:delete_all", "library:read_all"]


async def _read_item(test_engine, item_id: int) -> PrintQueueItem:
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as fresh:
        return (await fresh.execute(select(PrintQueueItem).where(PrintQueueItem.id == item_id))).scalar_one()


async def _login(async_client: AsyncClient, username: str, password: str) -> dict:
    login = await async_client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
async def users(async_client: AsyncClient) -> dict[str, dict]:
    """Auth on, plus one signed-in user per role. Returns headers by role."""
    setup = await async_client.post(
        "/api/v1/auth/setup",
        json={"auth_enabled": True, "admin_username": "approvaladmin", "admin_password": "AdminPass1!"},
    )
    assert setup.status_code == 200, setup.text
    admin = await _login(async_client, "approvaladmin", "AdminPass1!")

    headers = {}
    for role, perms in (
        ("requester", REQUESTER_PERMS),
        ("approver", APPROVER_PERMS),
        ("operator", OPERATOR_PERMS),
    ):
        group = await async_client.post(
            "/api/v1/groups/", headers=admin, json={"name": f"approval-{role}", "permissions": perms}
        )
        assert group.status_code == 201, group.text
        user = await async_client.post(
            "/api/v1/users/",
            headers=admin,
            json={"username": f"approval{role}", "password": "UserPass1!", "group_ids": [group.json()["id"]]},
        )
        assert user.status_code == 201, user.text
        headers[role] = await _login(async_client, f"approval{role}", "UserPass1!")
    return headers


@pytest.fixture
async def lib_file(db_session, tmp_path) -> LibraryFile:
    path = tmp_path / "benchy.gcode.3mf"
    path.write_bytes(b"not really a 3mf")
    lib = LibraryFile(
        filename="benchy.gcode.3mf",
        file_path=str(path),
        file_type="gcode.3mf",
        file_size=path.stat().st_size,
    )
    db_session.add(lib)
    await db_session.commit()
    await db_session.refresh(lib)
    return lib


async def _request(async_client, users, printer_id, lib_file, **extra):
    return await async_client.post(
        "/api/v1/queue/",
        headers=users["requester"],
        json={"printer_id": printer_id, "library_file_id": lib_file.id, **extra},
    )


class TestCreatingRequests:
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_request_is_staged_and_awaits_approval(
        self, async_client, users, printer_factory, lib_file, test_engine
    ):
        printer = await printer_factory()
        with patch(
            "backend.app.api.routes.print_queue.notification_service.on_queue_approval_requested",
            new=AsyncMock(),
        ) as notify:
            # The requester asks for ASAP at the top of the queue at a set time;
            # a request gets none of it.
            response = await _request(
                async_client,
                users,
                printer.id,
                lib_file,
                manual_start=False,
                insert_at_top=True,
                scheduled_time="2099-01-01T10:00:00Z",
            )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["requires_approval"] is True
        assert body["manual_start"] is True

        item = await _read_item(test_engine, body["id"])
        assert item.requires_approval is True
        assert item.manual_start is True
        assert item.scheduled_time is None
        notify.assert_awaited_once()
        assert notify.await_args.kwargs["requested_by"] == "approvalrequester"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_request_needs_a_printer_or_model(self, async_client, users, lib_file):
        response = await async_client.post(
            "/api/v1/queue/", headers=users["requester"], json={"library_file_id": lib_file.id}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_request_cannot_come_from_an_archive(self, async_client, users, printer_factory, archive_factory):
        printer = await printer_factory()
        archive = await archive_factory(printer.id)
        response = await async_client.post(
            "/api/v1/queue/",
            headers=users["requester"],
            json={"printer_id": printer.id, "archive_id": archive.id},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_queue_create_still_queues_normally(
        self, async_client, users, printer_factory, lib_file, test_engine
    ):
        printer = await printer_factory()
        response = await async_client.post(
            "/api/v1/queue/",
            headers=users["operator"],
            json={"printer_id": printer.id, "library_file_id": lib_file.id},
        )
        assert response.status_code == 200, response.text
        item = await _read_item(test_engine, response.json()["id"])
        assert item.requires_approval is False
        assert item.manual_start is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_library_bulk_add_makes_requests(self, async_client, users, printer_factory, lib_file, test_engine):
        printer = await printer_factory()
        no_target = await async_client.post(
            "/api/v1/library/files/add-to-queue", headers=users["requester"], json={"file_ids": [lib_file.id]}
        )
        assert no_target.status_code == 400

        response = await async_client.post(
            "/api/v1/library/files/add-to-queue",
            headers=users["requester"],
            json={"file_ids": [lib_file.id], "printer_id": printer.id},
        )
        assert response.status_code == 200, response.text
        item = await _read_item(test_engine, response.json()["added"][0]["queue_item_id"])
        assert item.requires_approval is True
        assert item.manual_start is True


class TestOnlyApproversHandleRequests:
    @pytest.fixture
    async def request_id(self, async_client, users, printer_factory, lib_file) -> int:
        printer = await printer_factory()
        response = await _request(async_client, users, printer.id, lib_file)
        assert response.status_code == 200, response.text
        return response.json()["id"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.parametrize("role", ["requester", "operator"])
    async def test_non_approver_cannot_touch_request(self, async_client, users, request_id, test_engine, role):
        headers = users[role]
        assert (await async_client.post(f"/api/v1/queue/{request_id}/start", headers=headers)).status_code == 403
        assert (
            await async_client.patch(f"/api/v1/queue/{request_id}", headers=headers, json={"manual_start": False})
        ).status_code == 403
        assert (await async_client.post(f"/api/v1/queue/{request_id}/cancel", headers=headers)).status_code == 403
        assert (await async_client.delete(f"/api/v1/queue/{request_id}", headers=headers)).status_code == 403

        bulk = await async_client.patch(
            "/api/v1/queue/bulk", headers=headers, json={"item_ids": [request_id], "manual_start": False}
        )
        assert bulk.status_code == 200
        assert bulk.json()["skipped_count"] == 1

        item = await _read_item(test_engine, request_id)
        assert item.status == "pending"
        assert item.requires_approval is True
        assert item.manual_start is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_approver_edit_keeps_request_staged(self, async_client, users, request_id, test_engine):
        response = await async_client.patch(
            f"/api/v1/queue/{request_id}", headers=users["approver"], json={"manual_start": False}
        )
        assert response.status_code == 200, response.text
        item = await _read_item(test_engine, request_id)
        assert item.manual_start is True
        assert item.requires_approval is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_approver_start_approves(self, async_client, users, request_id, test_engine):
        response = await async_client.post(
            f"/api/v1/queue/{request_id}/start?skip_filament_check=true", headers=users["approver"]
        )
        assert response.status_code == 200, response.text
        item = await _read_item(test_engine, request_id)
        assert item.requires_approval is False
        assert item.manual_start is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_approver_can_reject(self, async_client, users, request_id):
        response = await async_client.delete(f"/api/v1/queue/{request_id}", headers=users["approver"])
        assert response.status_code == 200, response.text
