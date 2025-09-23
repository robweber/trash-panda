__/api/check_config__ - Loads and checks the active configuration file for any errors that would prevent it from loading. If errors a present an `errors` key attempts to display a hint as to the error. 

__Success__
```
{
  "success": true,
  "message": "Config is valid"
}
```

__Error__
```
{
  "success": false,
  "message": "Configuration file is not valid",
  "errors": "{'bad_field': ['unknown field']}"
}
```
