"""Fixed-path HTTP adapter; browser requests from other origins cannot install code."""
from urllib.parse import urlsplit

from desk.app import Response
from .service import IntegrationError


def build_routes(service):
    def call(req, operation):
        headers = {key.lower(): value for key, value in req.headers.items()}
        origin = headers.get("origin")
        try:
            foreign = bool(origin and (urlsplit(origin).scheme != "http" or
                                      urlsplit(origin).netloc != headers.get("host")))
        except ValueError:
            foreign = True
        if req.method == "POST":
            if headers.get("sec-fetch-site") == "cross-site" or foreign:
                return Response(403, {"error": {"code": "origin_not_allowed", "message": "只能从台面设置页安装接入"}})
            if headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
                return Response(415, {"error": {"code": "invalid_content_type", "message": "请求须为 application/json"}})
        try:
            return Response(200, operation())
        except ValueError as error:
            return Response(400, {"error": {"code": "invalid_params", "message": str(error)}})
        except IntegrationError as error:
            return Response(error.http, {"error": {"code": error.code, "message": str(error)}})

    return [
        ("GET", "/api/pi-integration", lambda req: call(req, service.status)),
        ("POST", "/api/pi-integration", lambda req: call(req, lambda: service.apply(req.body.get("action")))),
        ("POST", "/api/pi-integration/check", lambda req: call(req, service.check)),
    ]
