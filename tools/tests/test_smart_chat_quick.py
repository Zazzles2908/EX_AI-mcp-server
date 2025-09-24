import asyncio
from tools.smart.smart_chat import SmartChatTool

async def main():
    t = SmartChatTool()
    print("requires_model:", t.requires_model())
    desc = t.get_descriptor()
    print("descriptor_name:", desc.get("name"))
    print("descriptor_has_schema:", isinstance(desc.get("input_schema"), dict))
    res = await t.execute({"prompt": "just a ping"})
    print("execute_len:", len(res))
    if res:
        item = res[0]
        text = getattr(item, 'text', str(item))
        print("execute_first_text:", text)

if __name__ == "__main__":
    asyncio.run(main())

