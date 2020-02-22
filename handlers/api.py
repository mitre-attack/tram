from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.requests import Request
from service.handler import ServiceHandler

handler = ServiceHandler()
api_core = FastAPI(openapi_prefix="/")
api_core.mount("/theme", StaticFiles(directory="webapp/theme"), name="static")
templates = Jinja2Templates(directory="webapp/html")


@api_core.get("/")
async def root(request: Request):
    index = dict(request=request)
    index['queue'] = await handler.data_svc.status_grouper("queue")
    index['in_review'] = await handler.data_svc.status_grouper("in_review")
    index['completed'] = await handler.data_svc.status_grouper("completed")
    return templates.TemplateResponse("index.html", index)

