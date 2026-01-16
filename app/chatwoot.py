from typing import Any, Dict, List, Optional

import httpx

from app.http_client import request_with_retries


class ChatwootClient:
    def __init__(
        self, base_url: str, account_id: str, inbox_id: str, api_token: str, timeout: float, retries: int
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.account_id = str(account_id)
        self.inbox_id = str(inbox_id)
        self.api_token = api_token
        self.retries = retries
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    def _headers(self) -> Dict[str, str]:
        return {"api_access_token": self.api_token}

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        response = await request_with_retries(
            self._client,
            method,
            url,
            self.retries,
            json=json,
            params=params,
            headers=self._headers(),
        )
        response.raise_for_status()
        if response.content:
            return response.json()
        return None

    def _extract_contact(self, data: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(data, dict):
            return data if isinstance(data, dict) else None
        payload = data.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("contact"), dict):
            return payload.get("contact")
        if isinstance(payload, list) and payload:
            first = payload[0]
            return first if isinstance(first, dict) else None
        if isinstance(data.get("contact"), dict):
            return data.get("contact")
        return data

    async def filter_contact_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        payload = {
            "payload": [
                {
                    "attribute_key": "email",
                    "filter_operator": "equal_to",
                    "values": [email],
                }
            ]
        }
        data = await self._request(
            "POST",
            f"/api/v1/accounts/{self.account_id}/contacts/filter",
            json=payload,
        )
        if not data:
            return None
        contacts = data.get("payload") if isinstance(data, dict) else None
        if isinstance(contacts, list):
            if not contacts:
                return None
            first = contacts[0]
            return first if isinstance(first, dict) else None
        return self._extract_contact(data)

    async def create_contact(self, name: str, email: str, chat_id: str) -> Dict[str, Any]:
        payload = {
            "inbox_id": self.inbox_id,
            "name": name,
            "email": email,
            "custom_attributes": {"chat_id": chat_id},
        }
        data = await self._request(
            "POST",
            f"/api/v1/accounts/{self.account_id}/contacts",
            json=payload,
        )
        contact = self._extract_contact(data)
        if not contact:
            raise ValueError("Chatwoot contact creation returned empty payload")
        return contact

    async def get_contact_conversations(self, contact_id: str) -> List[Dict[str, Any]]:
        data = await self._request(
            "GET",
            f"/api/v1/accounts/{self.account_id}/contacts/{contact_id}/conversations",
        )
        if isinstance(data, dict):
            conversations = data.get("payload")
        else:
            conversations = data
        if isinstance(conversations, list):
            return conversations
        return []

    async def create_conversation(self, contact_id: str, source_id: str) -> Dict[str, Any]:
        payload = {
            "source_id": source_id,
            "inbox_id": self.inbox_id,
            "contact_id": contact_id,
            "status": "open",
        }
        data = await self._request(
            "POST",
            f"/api/v1/accounts/{self.account_id}/conversations",
            json=payload,
        )
        return data

    async def create_message(self, conversation_id: str, message_type: str, content: str) -> Dict[str, Any]:
        payload = {"content": content, "message_type": message_type}
        data = await self._request(
            "POST",
            f"/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages",
            json=payload,
        )
        return data

    def pick_source_id(self, contact: Dict[str, Any]) -> Optional[str]:
        contact_inboxes = contact.get("contact_inboxes") if isinstance(contact, dict) else None
        if not isinstance(contact_inboxes, list):
            return None
        for inbox in contact_inboxes:
            if str(inbox.get("inbox_id")) == self.inbox_id:
                return inbox.get("source_id")
        if contact_inboxes:
            return contact_inboxes[0].get("source_id")
        return None

    def pick_conversation_by_inbox(
        self, conversations: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        for convo in conversations:
            if str(convo.get("inbox_id")) == self.inbox_id:
                return convo
        if conversations:
            return conversations[0]
        return None

    async def get_or_create_contact(self, name: str, email: str, chat_id: str) -> Dict[str, Any]:
        contact = await self.filter_contact_by_email(email)
        if contact:
            return contact
        return await self.create_contact(name=name or email, email=email, chat_id=chat_id)

    async def get_or_create_conversation(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        contact_id = str(contact.get("id"))
        conversations = await self.get_contact_conversations(contact_id)
        conversation = self.pick_conversation_by_inbox(conversations)
        if conversation:
            return conversation
        source_id = self.pick_source_id(contact)
        if not source_id:
            raise ValueError("Missing source_id for contact")
        return await self.create_conversation(contact_id=contact_id, source_id=source_id)
