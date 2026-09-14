const { chromium } = require("playwright");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

(async () => {
  const htmlPath = path.resolve("C:/dev/hpo-ptbr-lab/tmp/aula04_20260911/docx_qa_preview.html");
  const pdfPath = path.resolve("C:/dev/hpo-ptbr-lab/tmp/aula04_20260911/docx_qa_preview.pdf");
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "load" });
  await page.pdf({
    path: pdfPath,
    format: "Letter",
    printBackground: true,
    margin: { top: "1in", right: "1in", bottom: "1in", left: "1in" },
  });
  await browser.close();
  process.stdout.write(pdfPath + "\n");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
