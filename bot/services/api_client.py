import httpx
import structlog
import os

logger = structlog.get_logger()


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.secret = os.getenv("BOT_INTERNAL_SECRET", "my_super_secret_key_123")

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "X-Bot-Secret": self.secret,
                "X-Internal-Secret": self.secret,
                "Authorization": f"Bearer {self.secret}",
            },
            timeout=10.0,
        )

    async def register_user(
        self, telegram_id: int, full_name: str, username: str | None, language: str
    ) -> dict:
        try:
            response = await self._client.post(
                "/api/v1/users/register",
                json={
                    "telegram_id": telegram_id,
                    "full_name": full_name,
                    "username": username,
                    "language": language,
                },
            )
            logger.info("Register user response", status_code=response.status_code)
            return response.json()
        except Exception as e:
            logger.error("Register user request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def create_group(
        self,
        telegram_id: int,
        name: str,
        telegram_chat_id: int | None = None,
    ) -> dict:
        try:
            response = await self._client.post(
                "/api/v1/groups/create",
                json={
                    "telegram_id": telegram_id,
                    "name": name,
                    "telegram_chat_id": telegram_chat_id,
                },
            )
            logger.info("Create group response", status_code=response.status_code)
            return response.json()
        except Exception as e:
            logger.error("Create group request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def join_group(self, telegram_id: int, invite_code: str) -> dict:
        try:
            response = await self._client.post(
                "/api/v1/groups/join",
                json={"telegram_id": telegram_id, "invite_code": invite_code},
            )
            return response.json()
        except Exception as e:
            logger.error("Join group request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def link_group_by_code(self, telegram_id: int, invite_code: str, telegram_chat_id: int) -> dict:
        try:
            response = await self._client.post(
                "/api/v1/groups/link-by-code",
                json={
                    "telegram_id": telegram_id,
                    "invite_code": invite_code,
                    "telegram_chat_id": telegram_chat_id,
                },
            )
            return response.json()
        except Exception as e:
            logger.error("Link group request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def list_my_groups(self, telegram_id: int) -> dict:
        try:
            response = await self._client.get(f"/api/v1/groups/user/{telegram_id}")
            return response.json()
        except Exception as e:
            logger.error("List groups request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def list_group_tasks(self, group_id: int) -> dict:
        try:
            response = await self._client.get(f"/api/v1/tasks/group/{group_id}")
            return response.json()
        except Exception as e:
            logger.error("List group tasks request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def get_queue_preview(self, task_id: int) -> dict:
        try:
            response = await self._client.get(f"/api/v1/tasks/{task_id}/queue/preview")
            return response.json()
        except Exception as e:
            logger.error("Get queue preview request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def skip_queue(self, telegram_id: int, task_id: int) -> dict:
        try:
            response = await self._client.post(
                f"/api/v1/tasks/{task_id}/queue/skip",
                json={"telegram_id": telegram_id},
            )
            return response.json()
        except Exception as e:
            logger.error("Skip queue request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def delete_task(self, telegram_id: int, task_id: int) -> dict:
        try:
            response = await self._client.request(
                "DELETE",
                f"/api/v1/tasks/{task_id}",
                json={"telegram_id": telegram_id},
            )
            return response.json()
        except Exception as e:
            logger.error("Delete task request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def list_members(self, group_id: int) -> dict:
        try:
            response = await self._client.get(f"/api/v1/groups/{group_id}/members")
            return response.json()
        except Exception as e:
            logger.error("List members request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def swap_queue(
        self, telegram_id: int, task_id: int, entry_id_a: int, entry_id_b: int
    ) -> dict:
        try:
            response = await self._client.post(
                f"/api/v1/tasks/{task_id}/queue/swap",
                json={
                    "telegram_id": telegram_id,
                    "entry_id_a": entry_id_a,
                    "entry_id_b": entry_id_b,
                },
            )
            return response.json()
        except Exception as e:
            logger.error("Swap queue request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def create_task(
        self,
        telegram_id: int,
        group_id: int,
        name: str,
        description: str | None = None,
        schedule_type: str = "daily",
        reminder_interval_minutes: int = 60,
        require_photo: bool = True,
        schedule_interval_days: int | None = None,
        start_date: str | None = None,
    ) -> dict:
        try:
            response = await self._client.post(
                "/api/v1/tasks/",
                json={
                    "telegram_id": telegram_id,
                    "group_id": group_id,
                    "name": name,
                    "description": description,
                    "schedule_type": schedule_type,
                    "reminder_interval_minutes": reminder_interval_minutes,
                    "require_photo": require_photo,
                    "schedule_interval_days": schedule_interval_days,
                    "start_date": start_date,
                },
            )
            logger.info("Create task response", status_code=response.status_code)
            return response.json()
        except Exception as e:
            logger.error("Create task request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def set_vacation(self, telegram_id: int, member_id: int, is_on_vacation: bool) -> dict:
        try:
            response = await self._client.post(
                "/api/v1/groups/vacation",
                json={
                    "telegram_id": telegram_id,
                    "member_id": member_id,
                    "is_on_vacation": is_on_vacation,
                },
            )
            return response.json()
        except Exception as e:
            logger.error("Set vacation request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def get_member_statistics(self, member_id: int) -> dict:
        try:
            response = await self._client.get(f"/api/v1/statistics/member/{member_id}")
            return response.json()
        except Exception as e:
            logger.error("Get stats request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def get_my_tasks(self, telegram_id: int, group_id: int) -> dict:
        try:
            response = await self._client.get(
                f"/api/v1/tasks/member/{telegram_id}", params={"group_id": group_id}
            )
            return response.json()
        except Exception as e:
            logger.error("Get my tasks request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def complete_task_with_photo(
        self,
        task_id: int,
        telegram_id: int,
        photo_bytes: bytes | None,
        photo_filename: str | None,
        caption: str | None,
    ) -> dict:
        try:
            files = {}
            if photo_bytes:
                files["photo"] = (photo_filename or "photo.jpg", photo_bytes, "image/jpeg")
            data = {"telegram_id": str(telegram_id)}
            if caption:
                data["caption"] = caption

            response = await self._client.post(
                f"/api/v1/completion/{task_id}", data=data, files=files
            )
            return response.json()
        except Exception as e:
            logger.error("Complete task with photo request failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def close(self) -> None:
        await self._client.aclose()
