__/api/status/tag/<tag_id>__ - information on the status of each service with this tag id

```
{
  "id": "http",
  "name": "HTTP",
  "services": [
    {
      "check_attempt": 1,
      "id": "web-server-http",
      "host" {
        "id": "web-server",
        "name": "Web Server"
      }
      "last_state_change": "07-02-2022 11:40AM",
      "name": "HTTP",
      "return_code": 0,
      "state": "CONFIRMED",
      "text": "HTTP OK: HTTP/1.1 200 OK - 4410 bytes in 0.009 second response time",
      "raw_text": "HTTP OK: HTTP/1.1 200 OK - 4410 bytes in 0.009 second response time |time=0.009410s;;;0.000000;10.000000 size=4410B;;;0\n",
      "notifier": "none"
      "perf_data": [
        {
          "id": "time",
          "label": "time",
          "value": 0.009410,
          "min": 0.000000,
          "max": 10.000000,
          "uom": "s"
        }
      ]
    }
  ]
}

```
