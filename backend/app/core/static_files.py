from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class PosterStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        if path.startswith("poster/"):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Cache-Control"] = "public,max-age=300"
        return response
