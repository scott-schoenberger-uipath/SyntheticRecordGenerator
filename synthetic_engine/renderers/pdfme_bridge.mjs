import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
function argValue(flag) {
  const idx = args.indexOf(flag);
  if (idx === -1 || idx + 1 >= args.length) return '';
  return args[idx + 1];
}

const templatePath = argValue('--template-json');
const inputsPath = argValue('--inputs-json');
const outPath = argValue('--out');

if (!templatePath || !inputsPath || !outPath) {
  console.error('Usage: node pdfme_bridge.mjs --template-json <path> --inputs-json <path> --out <pdf>');
  process.exit(2);
}

const { generate } = await import('@pdfme/generator');
const schemas = await import('@pdfme/schemas');
const plugins = {
  text: schemas.text,
};
if (schemas.image) {
  plugins.image = schemas.image;
}

const template = JSON.parse(fs.readFileSync(templatePath, 'utf8'));
const inputs = JSON.parse(fs.readFileSync(inputsPath, 'utf8'));

const pdf = await generate({ template, inputs, plugins });
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, pdf);
console.log(`wrote ${outPath}`);
