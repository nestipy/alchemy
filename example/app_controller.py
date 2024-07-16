from typing import Annotated

from nestipy.common import Controller, Get, Post, Put, Delete
from nestipy.ioc import Inject, Body, Param
from nestipy.openapi import ApiOkResponse, ApiBody
from app_service import AppService
from dto import CreateUserDto


@ApiOkResponse()
@Controller()
class AppController:
    service: Annotated[AppService, Inject()]

    @Get()
    async def get(self) -> str:
        return await self.service.get()

    @ApiBody(CreateUserDto)
    @Post()
    async def post(self, data: Annotated[CreateUserDto, Body()]) -> str:
        return await self.service.post(data=data)

    @Put('/{id}')
    async def put(self, _id: Annotated[int, Param('id')], data: Annotated[dict, Body()]) -> str:
        return await self.service.put(id_=_id, data=data)

    @Delete('/{id}')
    async def delete(self, _id: Annotated[int, Param('id')]) -> None:
        await self.service.delete(id_=_id)
