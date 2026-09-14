from packages.platform.service import create_service_app

from .api.upload import router as upload_router
from .services.storage import Storage

app = create_service_app("media")
app.state.storage = Storage()
app.include_router(upload_router)
