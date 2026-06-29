__/api/status/services__ - a list of services, can be filtered by return code and service ID using query parameters. By default all services are returned.

__Return Code Example:__
 - only return services with a status of 1 or 2 (warning or critical)
 - `http://localhost:3000/api/status/services?return_codes=1|2`

__Service Filter Example:__
 - return any services where the ID contains the word _alive_
 - `http://localhost:3000/api/status/services?service_filter=alive`

```
{
  "return_codes": [
    "1",
    "2"
  ],
  "services": [
    {
      "check_attempt": 1,
      "id": "alive",
      "last_state_change": "07-02-2022 11:40AM",
      "name": "Alive",
      "return_code": 2,
      "state": "CONFIRMED",
      "text": "Ping unsuccessfull!",
      "raw_text": "Ping unsuccessfull!|percent_packet_loss=100.0% average_return_time=20.0ms"
      "perf_data": [
        {
          "id": "percent-packet-loss",
          "label": "percent_packet_loss",
          "uom": "%",
          "value": 100
        },
        {
          "id": "average-return-time",
          "label": "average_return_time",
          "uom": "ms",
          "value": 20.0
        }
      ]
    }
  ]
}
```
