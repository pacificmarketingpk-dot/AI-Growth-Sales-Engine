"""Checks every page at 390/430/768/1024/1280/1440px for sideways scrolling and sub-32px tap targets.
Run after acceptance.py (it signs in as the account that test creates).  BASE_URL=http://localhost python e2e/responsive.py
"""
import asyncio
from playwright.async_api import async_playwright
import os
B=os.environ.get("BASE_URL","http://localhost")
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch()
        pg = await (await br.new_context(viewport={"width":1440,"height":900})).new_page()
        await pg.goto(B); await pg.fill("input[type=email]","ayesha@example.com"); await pg.fill("input[type=password]","correct-horse-1")
        await pg.click("button[type=submit]"); await pg.wait_for_selector("text=Recent activity")
        pages=["/","/prospects","/prospects/1","/analysis","/hot-leads","/conversations","/outreach","/meetings","/calendar","/analytics","/settings"]
        bad=[]
        for w in [390,430,768,1024,1280,1440]:
            await pg.set_viewport_size({"width":w,"height":900})
            for path in pages:
                await pg.goto(B+path); await pg.wait_for_timeout(700)
                ow = await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                small = await pg.evaluate("""() => [...document.querySelectorAll('main button, main a, main select, main input:not([type=checkbox]):not([type=range])')].filter(e=>{const r=e.getBoundingClientRect(); return r.width>0 && r.height>0 && r.height<32}).length""")
                if ow>0: bad.append((w,path,"overflow",ow))
                if w<=430 and small>0: bad.append((w,path,"small-targets",small))
        print("issues:", bad or "none")
        await pg.set_viewport_size({"width":390,"height":844})
        await pg.set_viewport_size({"width":1440,"height":900})
        await br.close()
asyncio.run(main())
