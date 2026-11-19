"""Public URL/domain facade."""


async def check_url(service, value):
    return await service.check("url", value)


async def check_domain(service, value):
    return await service.check("domain", value)
