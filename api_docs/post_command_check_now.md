__/api/command/check_now/<host_id>__ - updates a given host's next check time to the current time. This forces a service check instead of waiting for the normal update interval. The host id can be found via the `/api/status` endpoint for each host.

```
{
  "success": true
  "next_check": "09-14-2022 09:44AM"
}
```
