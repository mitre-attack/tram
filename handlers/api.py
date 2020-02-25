from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.requests import Request
from service.handler import ServiceHandler

import json

handler = ServiceHandler()
api_core = FastAPI(openapi_prefix="/")
api_core.mount("/theme", StaticFiles(directory="webapp/theme"), name="static")
templates = Jinja2Templates(directory="webapp/html")


@api_core.get("/")
async def root(request: Request):
    index = dict(request=request)
    index['needs_review'] = await handler.data_svc.status_grouper("needs_review")
    index['queue'] = await handler.data_svc.status_grouper("queue")
    index['in_review'] = await handler.data_svc.status_grouper("in_review")
    index['completed'] = await handler.data_svc.status_grouper("completed")
    return templates.TemplateResponse("index.html", index)

@api_core.get("/about")
async def about(request: Request):
    return templates.TemplateResponse("about.html",{"request":request})

@api_core.post("/rest")
async def report_submit(request: Request):
    data = dict(await request.json())
    index = data.pop('index')
    options = dict(
        false_positive=lambda d: handler.rest_svc.false_positive(criteria=d),
        true_positive=lambda d: handler.rest_svc.true_positive(criteria=d),
        false_negative=lambda d: handler.rest_svc.false_negative(criteria=d),
        set_status=lambda d: handler.rest_svc.set_status(criteria=d),
        insert_report=lambda d: handler.rest_svc.insert_report(criteria=d),
        insert_csv=lambda d: handler.rest_svc.insert_csv(criteria=d),
        remove_sentences=lambda d: handler.rest_svc.remove_sentences(criteria=d),
        delete_report=lambda d: handler.rest_svc.delete_report(criteria=d),
        sentence_context=lambda d: handler.rest_svc.sentence_context(criteria=d),
        confirmed_sentences=lambda d: handler.rest_svc.confirmed_sentences(criteria=d),
        missing_technique=lambda d: handler.rest_svc.missing_technique(criteria=d)
    )
    result = await options[index](data)
    return result

@api_core.get("/edit/{title}")
async def report_view(request: Request,title: str):
    report = await handler.dao.get('reports', dict(title=title))
    sentences = await handler.data_svc.build_sentences(report[0]['uid'])
    attack_uids = await handler.dao.get('attack_uids')
    original_html = await handler.dao.get('original_html', dict(report_uid=report[0]['uid']))
    final_html = await handler.web_svc.build_final_html(original_html, sentences)
    output = dict(request=request,file=title, title=title, sentences=sentences, attack_uids=attack_uids, original_html=original_html, final_html=final_html)
    return templates.TemplateResponse('columns.html',output)

@api_core.get("/export/nav/{title}")
async def nav_export(request: Request,title: str):
    # Get the report from the database
    report = await handler.dao.get('reports', dict(title=title))
    # Create the layer name and description
    report_title = report[0]['title']
    layer_name = f"{report_title}"
    enterprise_layer_description = f"Enterprise techniques used by {report_title}, ATT&CK"
    version = '1.0'
    if (version): # add version number if it exists
        enterprise_layer_description += f" v{version}"
    # Enterprise navigator layer
    enterprise_layer = {}
    enterprise_layer['name'] = layer_name
    enterprise_layer['description'] = enterprise_layer_description
    enterprise_layer['domain'] = "mitre-enterprise"
    enterprise_layer['version'] = "2.2"
    enterprise_layer['techniques'] = []
    enterprise_layer["gradient"] = { # white for nonused, blue for used
        "colors": ["#ffffff", "#66b1ff"],
        "minValue": 0,
        "maxValue": 1
    }
    enterprise_layer['legendItems'] = [{
        'label': f'used by {report_title}',
        'color': "#66b1ff"
    }]

    # Get confirmed techniques for the report from the database
    techniques = await handler.data_svc.get_confirmed_techniques(report[0]['uid'])

    # Append techniques to enterprise layer
    for technique in techniques:
        enterprise_layer['techniques'].append(technique)
        
    # Return the layer JSON in the response
    layer = json.dumps(enterprise_layer)
    return layer