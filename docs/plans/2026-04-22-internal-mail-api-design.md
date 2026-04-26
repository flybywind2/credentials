# Internal Mail API Design

**Goal:** Send approval notification emails through the company mail API.

## Approach

Keep the existing `EmailService` boundary and support `mail_api` alongside `disabled`. Approval code continues to call `_notify()` with `EmailMessage`; only the delivery implementation changes.

## Configuration

`MAIL_MODE=mail_api` selects the company API sender. The service reads `MAIL_API_BASE_URL`, optional `MAIL_API_SYSTEM_ID`, timeout, and payload format from environment variables. This preserves the current deployment style and keeps environment-specific values outside source control.

## Request Shape

The service posts to:

```text
{MAIL_API_BASE_URL}/send_mail
```

`MAIL_API_BASE_URL=mail.net` resolves to `https://mail.net/send_mail`. If `MAIL_API_BASE_URL` already ends with `/send_mail`, the service uses it as-is.

The default body format is JSON. A `MAIL_API_PAYLOAD_FORMAT=form` option is supported for deployments where the API gateway requires request parameters instead of JSON. The `recipients` list is serialized as a JSON string in form mode.

## Error Handling

The service calls `raise_for_status()` on the API response. Existing approval notification code already catches delivery exceptions and logs them without blocking approval workflow completion.

## Testing

Add tests for `/send_mail` URL mapping, JSON payload mapping, service selection, and runtime environment validation. Existing disabled-mode tests remain unchanged.
