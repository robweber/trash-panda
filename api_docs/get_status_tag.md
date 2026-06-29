__/api/status/tag/<type>/<tag_id>__ - return the status information for all hosts or services attached to this tag. Must specify either __host__ or __service_- as the type. Returned response will have __members__ as the resulting key.

```
{
  "id": "http",
  "name": "HTTP",
  "members": [
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
