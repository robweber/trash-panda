__/api/time/<perf_id>/start>/<end>__ - lookup Performance Data information for a specified time period. The __start__ and __end__ times should be unix timestamps. If these are omitted the last 60 minutes are returned by default.

The performance ID is created by combining the host and service ids. For a host __switch-1__ with a service __alive__ the performance id would be __switch-1-alive__.

```
{
  "times": [
    "04/14/24 10:03:00",
    "04/14/24 10:08:00",
    "04/14/24 10:13:00",
    "04/14/24 10:17:00",
    "04/14/24 10:21:00",
    "04/14/24 10:26:00",
    "04/14/24 10:31:00"
  ],
  "unix_times": [
    1713106980.0,
    1713107280.0,
    1713107580.0,
    1713107820.0,
    1713108060.0,
    1713108360.0,
    1713108660.0
  ],
  "values": [
    0.07799999999999999,
    0.082,
    0.146,
    0.074,
    0.066,
    0.076,
    0.132
  ]
}
```
