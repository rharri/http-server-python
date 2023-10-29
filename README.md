## Description
A simple HTTP server based on my submission for "Build Your Own HTTP Server" challenge.

See: https://github.com/between-compiles/codecrafters-http-server-python

## Usage
Running the server from the command line:

Start the server in the background
```
$ python main.py &
[1] 6152
```

Send a curl request
```
$ curl -v http://127.0.0.1:4221/
*   Trying 127.0.0.1:4221...
* Connected to 127.0.0.1 (127.0.0.1) port 4221 (#0)
> GET / HTTP/1.1
> Host: 127.0.0.1:4221
> User-Agent: curl/8.1.2
> Accept: */*
> 
< HTTP/1.1 200 OK
* no chunk, no close, no size. Assume close to signal end
< 
* Closing connection 0
```

Foreground the server process and use ```CTRL+C``` to quit the server

```
$ fg
[1]  + running    python main.py
^CGoodbye!
```