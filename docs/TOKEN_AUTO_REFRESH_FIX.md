# Token Auto-Refresh Issue - Resolved

## Issue

User experiencing 401 Unauthorized errors when running `tp today`. The error message was unclear and didn't indicate the root cause.

## Root Cause

The credentials file (`~/.local/share/todopro-cli/default.credentials.json`) only contained an access token but was missing the refresh token:

```json
{
  "token": "eyJhbGci..."
}
```

Without a refresh_token, the auto-refresh mechanism cannot work, even though it was properly implemented.

## Solution Implemented

### 1. Improved Error Messaging

Modified `src/todopro_cli/api/client.py` to provide a clear, helpful error message when token refresh fails due to missing refresh_token:

```python
# Before (generic 401 error)
Error: Failed to get today's tasks: Client error '401 Unauthorized'

# After (helpful error message)
⚠ Your session has expired and no refresh token is available.
Please login again: todopro login

Error: Failed to get today's tasks: Client error '401 Unauthorized'
```

### 2. Verified Auto-Refresh is Enabled

Confirmed that auto-refresh is enabled by default in the configuration:

```python
class AuthConfig(BaseModel):
    """Authentication configuration."""
    auto_refresh: bool = Field(default=True)
```

### 3. Verified Token Refresh Logic Works

The token refresh logic in `APIClient.request()` is properly implemented:

1. On 401 error, attempts to refresh token
2. Uses refresh_token to get new access_token
3. Retries the original request with new token
4. If refresh fails, shows helpful error message

## How Token Refresh Works

### Normal Flow (with refresh_token)

```
1. Request fails with 401 Unauthorized
   ↓
2. Check if refresh_token exists
   ↓
3. Call /v1/auth/refresh endpoint
   ↓
4. Receive new access_token (and optionally new refresh_token)
   ↓
5. Save new tokens to credentials file
   ↓
6. Retry original request with new access_token
   ↓
7. Success!
```

### Failure Flow (without refresh_token)

```
1. Request fails with 401 Unauthorized
   ↓
2. Check if refresh_token exists → NOT FOUND
   ↓
3. Show helpful error message:
   "⚠ Your session has expired and no refresh token is available.
    Please login again: todopro login"
   ↓
4. Raise original 401 error
```

## Files Modified

- `src/todopro_cli/api/client.py` - Added helpful error message for missing refresh_token

## Resolution for User

The user needs to re-login to obtain a refresh_token:

```bash
todopro login
# Or
tp login
```

This will save credentials with both access_token and refresh_token:

```json
{
  "token": "eyJhbGci...",
  "refresh_token": "eyJhbGci..."
}
```

After re-login, the auto-refresh mechanism will work automatically.

## Testing

### Manual Test

1. **With refresh_token** - Token auto-refreshes on 401
2. **Without refresh_token** - Shows helpful error message

### Automated Tests

The token refresh logic is tested in `tests/test_api_client.py`:

```bash
uv run pytest tests/test_api_client.py -v -k refresh
```

## Prevention

To prevent this issue in the future:

1. **Always save refresh_token** - The login command already does this correctly
2. **Clear error messages** - Now implemented
3. **Documentation** - Users understand they need to re-login if tokens are missing

## Verification

After the fix, the error message is now clear and actionable:

```bash
$ tp today

⚠ Your session has expired and no refresh token is available.
Please login again: todopro login

Error: Failed to get today's tasks: Client error '401 Unauthorized'
```

The user knows exactly what to do: run `todopro login`.

## Future Enhancements

Potential improvements:

1. Add `todopro whoami` check before commands to verify authentication
2. Automatic prompt to login when credentials are missing/expired
3. Show token expiration time in `todopro whoami`
4. Add `--force-refresh` flag to manually trigger token refresh
