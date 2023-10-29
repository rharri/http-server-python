# main.py
# !/usr/bin/env python3

"""A simple HTTP server."""

import http
import pathlib
import socket
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any, NamedTuple


class HttpRequest(NamedTuple):
    """Represents a HTTP request message."""
    http_method: http.HTTPMethod = None
    request_target: str = None
    header_fields: dict[str: str] = {}
    injected: dict[str: Any] = {}
    body: str = None


class HttpResponse(NamedTuple):
    """Represents a HTTP response message."""
    http_status: http.HTTPStatus = None
    content_type: str = None
    body: str = None


class Router:
    """Simple router that maps paths to handlers."""

    def __init__(self) -> None:
        self.route_table = {}

    def add_route(self, method: http.HTTPMethod, route: str, handler):
        self.route_table[method + route] = handler

    def dispatch(self, http_request: HttpRequest) -> HttpResponse:
        # This router only uses part of the path to resolve the route
        route = "".join(pathlib.Path(http_request.request_target).parts[:2])

        handler = self.route_table.get(http_request.http_method + route)
        return handler(http_request) if handler else HttpResponse(http.HTTPStatus.NOT_FOUND)


def handle_root(http_request: HttpRequest) -> HttpResponse:
    return HttpResponse(http.HTTPStatus.OK)


def handle_echo(http_request: HttpRequest) -> HttpResponse:
    # Take everything after /echo/
    body = f"{http_request.request_target.partition('/echo/')[2]}"
    return HttpResponse(http.HTTPStatus.OK, content_type="text/plain", body=body)


def handle_user_agent(http_request: HttpRequest) -> HttpResponse:
    body = f"{http_request.header_fields['User-Agent']}"
    return HttpResponse(http.HTTPStatus.OK, content_type="text/plain", body=body)


def handle_read_file(http_request: HttpRequest) -> HttpResponse:
    file_name = f"{http_request.request_target.partition('/files/')[2]}"
    read_path = pathlib.Path(http_request.injected["directory"]).joinpath(file_name)

    if read_path.exists():
        body = read_path.read_text()
        return HttpResponse(http.HTTPStatus.OK, content_type="application/octet-stream", body=body)
    else:
        return HttpResponse(http.HTTPStatus.NOT_FOUND)


def handle_write_file(http_request: HttpRequest) -> HttpResponse:
    file_name = f"{http_request.request_target.partition('/files/')[2]}"
    write_directory = pathlib.Path(http_request.injected["directory"])
    write_path = write_directory.joinpath(file_name)

    if write_directory.exists():
        write_path.write_text(http_request.body)
        return HttpResponse(http.HTTPStatus.CREATED)
    else:
        return HttpResponse(http.HTTPStatus.INTERNAL_SERVER_ERROR)


def parse_request(request_data: bytes, **injected) -> HttpRequest:
    """Parse the provided request data into a HttpRequest.
    
    Args:
        request_data: Bytes of the request data.
        injected: Dictionary of values to augment the HTTP request message.
    
    Returns:
        A representation of a HttpRequest.
    """
    http_message: str = request_data.decode("utf-8")

    http_method, request_target = parse_start_line(http_message)
    header_fields = parse_header(http_message)
    body = parse_body(http_message)

    return HttpRequest(http_method, request_target, header_fields, injected, body)


def parse_start_line(http_message: str) -> (http.HTTPMethod, str):
    """Parse the start line of an HTTP message.

    Args:
        http_message: String of the HTTP message to parse.

    Returns:
        Tuple of the method and request target of the HTTP message. 
    """
    # The HTTP message start line is the first line in the HTTP request
    request_line = http_message.split("\r\n")[0]

    # The request target is the second value of the HTTP message start line
    http_method, request_target, _ = request_line.split(" ")

    return http.HTTPMethod(http_method), request_target


def parse_header(http_message: str) -> dict[str: str]:
    """Parse the header fields of an HTTP message.

    The field name is the key and the field value is the value of the
    dictionary.

    Args:
        http_message: String of the HTTP message to parse.

    Returns:
        Dictionary of header fields of the HTTP message. Empty
        dictionary if no header fields are found.     
    """
    header_fields = {}
    for field in http_message.split("\r\n"):
        if ":" in field:
            field_name, _, field_value = field.partition(":")
            header_fields[field_name] = field_value.strip()
    return header_fields


def parse_body(http_message: str):
    """Parse the body of an HTTP message.

    Args:
        http_message: String of the HTTP message to parse.

    Returns:
        String of the body. Empty string if a body is not present.
    """
    return http_message.split("\r\n")[-1]


def serialize(resp: HttpResponse) -> bytearray:
    """Serialize the HTTP response message for transport."""
    start_line = f"HTTP/1.1 {resp.http_status.value} " \
                 f"{resp.http_status.phrase}\r\n\r\n".encode("ascii")

    data = bytearray()
    data.extend(start_line)

    if resp.body:
        # Remove the last \r\n as the HTTP message does not end here
        data = data[:-2]
        data.extend(f"Content-Type: {resp.content_type}\r\n".encode("ascii"))
        data.extend(f"Content-Length: {len(resp.body)}\r\n\r\n".encode("ascii"))
        data.extend(resp.body.encode("utf-8"))

    return data


def serve_client(client_socket: socket, router: Router, directory: str):
    # Get the data (as bytes) from the client socket
    client_data_buffer = client_socket.recv(4096)
    http_request = parse_request(client_data_buffer, directory=directory)
    http_response = router.dispatch(http_request)
    client_socket.send(serialize(http_response))
    client_socket.close()


def main(args: list[str]):
    directory = args[2] if "--directory" in args else None

    router = Router()
    router.add_route(http.HTTPMethod.GET, "/", handle_root)
    router.add_route(http.HTTPMethod.GET, "/echo", handle_echo)
    router.add_route(http.HTTPMethod.GET, "/user-agent", handle_user_agent)
    router.add_route(http.HTTPMethod.GET, "/files", handle_read_file)
    router.add_route(http.HTTPMethod.POST, "/files", handle_write_file)

    # Create a thread pool of worker threads to handle client connections 
    with ThreadPoolExecutor() as executor:
        # Create a TCP socket bound to local host
        with socket.create_server(("127.0.0.1", 4221), reuse_port=True) \
                as server_socket:
            # Run until interrupted
            while True:
                # Wait for the client connection
                client_socket, _ = server_socket.accept()
                executor.submit(serve_client, client_socket, router, directory)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        print("Goodbye!")
