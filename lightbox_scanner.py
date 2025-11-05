
import asyncio
from playwright.async_api import async_playwright
from openpyxl import Workbook
from collections import Counter

URLS = [
    "https://www.uob.com.sg/personal/ajax-category-page-filter.page",
    "https://www.uob.com.sg/personal/cards/index.page",
    "https://www.uob.com.sg/personal/highlights/solutions/for-the-ladies.page",
]
OUTPUT_XLSX = "lightbox_report_urls.xlsx"
WAIT_TIME = 5
LOAD_MORE_SELECTOR = 'button:has-text("Load More")'

async def scan_url(playwright, url):
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    await page.goto(url)
    await page.wait_for_timeout(WAIT_TIME * 1000)

    for _ in range(5):
        try:
            load_more = await page.query_selector(LOAD_MORE_SELECTOR)
            if load_more:
                await load_more.click()
                await page.wait_for_timeout(2000)
            else:
                break
        except Exception:
            break

    result = {"url": url, "lightboxes": set(), "missing_anchors": set()}
    modals = await page.query_selector_all(".modal-lightbox[id]")
    for modal in modals:
        modal_id = await modal.get_attribute("id")
        result["lightboxes"].add(modal_id)
        anchor = await page.query_selector(f'a[href="#{modal_id}"]')
        if not anchor:
            result["missing_anchors"].add(modal_id)

    await browser.close()
    return result

async def main():
    async with async_playwright() as playwright:
        tasks = [scan_url(playwright, url) for url in URLS]
        results = await asyncio.gather(*tasks)

        lightbox_to_urls = {}
        missing_anchors_report = []

        for r in results:
            url = r["url"]
            for lb_id in r["lightboxes"]:
                lightbox_to_urls.setdefault(lb_id, []).append(url)
            for missing_id in r["missing_anchors"]:
                missing_anchors_report.append((url, missing_id))

        all_lightboxes = [lb for r in results for lb in r["lightboxes"]]
        duplicates = [lb for lb, count in Counter(all_lightboxes).items() if count > 1]

        wb = Workbook()
        ws1 = wb.active
        ws1.title = "Missing Anchors"
        ws1.append(["URL", "Lightbox ID Missing Anchor"])
        for url, lb_id in missing_anchors_report:
            ws1.append([url, lb_id])

        ws2 = wb.create_sheet(title="Shared Lightboxes")
        ws2.append(["Lightbox ID", "URLs"])
        for lb in sorted(duplicates):
            ws2.append([lb, ", ".join(sorted(lightbox_to_urls[lb]))])

        wb.save(OUTPUT_XLSX)
        print(f"✅ Report saved to {OUTPUT_XLSX}")

asyncio.run(main())
