__/api/health__ - basic program health. Status is set to _Offline_ if the main system checking loop hasn't run in over 2 minutes. This should look for services to check every 60 seconds when running properly.

```
{
  "last_check_time": "07-05-2022 12:00PM",
  "text": "Online",
  "return_code": 0
}
```
