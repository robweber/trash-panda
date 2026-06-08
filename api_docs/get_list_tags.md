__/api/list/tags__ - prints a list of all tags on the system as dictionary of tag id and given name. By default all tags are returned.

Optionally a query parameter __type__ can be used to filter on tags belonging to an asset type (host or service)

`http://localhost:3000/api/list/tags?type=host`

```
{
  "disk-space": "Disk Space",
  "backups": "Backups"
}
```
