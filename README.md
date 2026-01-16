# Chatwoot <> LinkedIn Bridge (Unipile)

## Setup

1. Create the Supabase tables:

```sql
-- run supabase.sql in your Supabase SQL editor
```

2. Copy `.env.example` to `.env` and fill values.

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Webhooks

- Chatwoot -> `POST /webhook/chatwoot`
- Unipile -> `POST /webhook/unipile`

Both accept `X-Webhook-Secret` if `WEBHOOK_SECRET` is set.

## curl examples

### Chatwoot outgoing

```bash
curl -X POST http://localhost:8000/webhook/chatwoot \
  -H 'Content-Type: application/json' \
  -H 'X-Webhook-Secret: change_me' \
  -d '{
    "event": "message_created",
    "message_type": "outgoing",
    "content": "Hello from Chatwoot",
    "conversation": {
      "meta": {
        "sender": {
          "custom_attributes": {
            "chat_id": "1Mha-KY4UaGmFPHDm1a7RQ"
          }
        }
      }
    }
  }'
```

### Unipile incoming (normal JSON)

```bash
curl -X POST http://localhost:8000/webhook/unipile \
  -H 'Content-Type: application/json' \
  -H 'X-Webhook-Secret: change_me' \
  -d '{
    "event": "message_received",
    "chat_id": "1Mha-KY4UaGmFPHDm1a7RQ",
    "message": "Hello from LinkedIn",
    "is_sender": false,
    "attendees": [
      {"attendee_id": "RcVEq8W3XVSFa5wbO5nRfA", "attendee_name": "Joao Lucas"}
    ]
  }'
```

### Unipile incoming (wrapped string)

```bash
curl -X POST http://localhost:8000/webhook/unipile \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'X-Webhook-Secret: change_me' \
  --data-urlencode '{"event":"message_received","chat_id":"1Mha-KY4UaGmFPHDm1a7RQ","message":"Hello","is_sender":true,"attendees":[{"attendee_id":"RcVEq8W3XVSFa5wbO5nRfA","attendee_name":"Joao Lucas"}]}'
```

## Dashboard (optional)

```bash
streamlit run dashboard.py
```
