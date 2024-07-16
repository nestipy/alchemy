import uvicorn
from nestipy.core import NestipyFactory
from nestipy.openapi import SwaggerModule, DocumentBuilder

from app_module import AppModule

app = NestipyFactory.create(AppModule)

doc = DocumentBuilder().set_title("SQL Alchemy sample").set_description("Using Async sqlalchemy with nestipy").build()
SwaggerModule.setup('api', app, doc)

if __name__ == '__main__':
    uvicorn.run('main:app', host="0.0.0.0", port=8000, reload=True)
