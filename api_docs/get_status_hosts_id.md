__/api/status/host__ - status information for the host with the given id. Output is same as `/api/status/hosts` but will all host services (`services` key) as well.

```
[
  {
    "alive": 0,
    "config": {
      "community": "public"
    },
    "icon": "router-network",
    "id": "switch-1",
    "info": "This device type will work with generic managed switches. SNMP information must be correct and setup on the switch for services to properly be queried.",
    "ip": "192.168.0.1",
    "name": "Switch 1",
    "overall_status": 1,
    "interval": 3,
    "service_check_attempts": 2,
    "last_check": "07-21-2022 11:01AM",
    "next_check": "07-21-2022 11:04AM",
    "silenced": false,
    "type": "switch",
    "services":
    [
      {
        "name": "Alive",
        "return_code": 1,
        "text": "Ping successfull!",
        "raw_text": "Ping successfull!|percent_packet_loss=0.0% average_return_time=0.06599999999999999ms",
        "id": "batman-alive",
        "check_attempt": 1,
        "state": "CONFIRMED",
        "last_state_change": "04-08-2024 02:11PM",
        "host": {
          "id": "switch-1",
          "name": "Switch 1"
        },
        "tags": [],
        "perf_data": [
          {
            "value": 0,
            "id": "switch-1-alive-percent-packet-loss",
            "label": "percent_packet_loss",
            "uom": "%"
          },
          {
            "value": 0.06599999999999999,
            "id": "switch-1-alive-average-return-time",
            "label": "average_return_time",
            "uom": "ms"
          }
        ]
      }
    ]
  }
]
```
