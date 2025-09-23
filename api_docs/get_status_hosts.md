__/api/status/hosts__ - detailed listing of the status of each host. This does not include service information, use `/api/status/host/<host_id>` to get the full listing with services.

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
    "type": "switch"
  }
]
```
