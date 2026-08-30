#!/usr/bin/env node
// Renders the synthetic corpus (T60) from HTML templates to PDF.
//
// Playwright is already a dev dependency for the e2e suite, so this needs no
// new tooling. Output is committed, so a test run never depends on a browser
// being installed.
//
// Every value below is invented. National register numbers use an obviously
// fake 00.00.00-000.00 shape so nothing here can be mistaken for real data.
import { readFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = dirname(here);
// Resolved from the frontend's node_modules rather than by bare specifier:
// this script lives under backend/, where Node would not find the package.
const repoRoot = dirname(dirname(dirname(root)));
const { chromium } = await import(
  pathToFileURL(join(repoRoot, 'frontend/node_modules/playwright/index.mjs')).href
);
const css = readFileSync(join(root, 'templates/base.css'), 'utf8');
const out = join(root, 'documents');
mkdirSync(out, { recursive: true });

const money = (n) => '€ ' + n.toLocaleString('nl-BE', { minimumFractionDigits: 2 });

const payslip = (d) => `
<h1>Loonfiche — ${d.period}</h1>
<div class="org">${d.employer} · Ondernemingsnummer 0000.000.000</div>
<div class="meta">Werknemer: ${d.employee}<br>Rijksregisternummer: 00.00.00-000.00</div>
<table>
  <tr><th>Omschrijving</th><th class="right">Bedrag</th></tr>
  <tr><td>Brutoloon</td><td class="right">${money(d.gross)}</td></tr>
  <tr><td>RSZ-bijdrage</td><td class="right">- ${money(d.rsz)}</td></tr>
  <tr><td>Bedrijfsvoorheffing</td><td class="right">- ${money(d.tax)}</td></tr>
  <tr class="total"><td>Netto te betalen</td><td class="right">${money(d.net)}</td></tr>
</table>
<div class="stamp">Dit is een fictief document, aangemaakt voor testdoeleinden.</div>`;

const taxAssessment = (d) => `
<h1>Aanslagbiljet personenbelasting</h1>
<div class="org">FOD Financiën · Aanslagjaar ${d.year}</div>
<div class="meta">Belastingplichtige: ${d.name}<br>Rijksregisternummer: 00.00.00-000.00</div>
<table>
  <tr><th>Omschrijving</th><th class="right">Bedrag</th></tr>
  <tr><td>Gezamenlijk belastbaar inkomen</td><td class="right">${money(d.gross)}</td></tr>
  <tr class="total"><td>Netto belastbaar inkomen</td><td class="right">${money(d.net)}</td></tr>
</table>
<div class="stamp">Fictief document voor testdoeleinden.</div>`;

const accountant = (d) => `
<h1>Attest van de boekhouder</h1>
<div class="org">${d.firm} · ITAA-nummer 00.000.000</div>
<div class="meta">Betreft: ${d.name}<br>Boekjaar ${d.year}</div>
<table>
  <tr><th>Omschrijving</th><th class="right">Bedrag</th></tr>
  <tr><td>Omzet</td><td class="right">${money(d.turnover)}</td></tr>
  <tr class="total"><td>Netto jaarinkomen</td><td class="right">${money(d.net)}</td></tr>
</table>
<div class="stamp">Fictief document voor testdoeleinden.</div>`;

const employer = (d) => `
<h1>Werkgeversattest</h1>
<div class="org">${d.employer}</div>
<div class="meta">
  Werknemer: ${d.employee}<br>
  Type contract: ${d.contract}<br>
  In dienst sinds: ${d.start}<br>
  Bruto jaarsalaris: ${money(d.gross)}
</div>
<div class="stamp">Fictief document voor testdoeleinden.</div>`;

const loan = (d) => `
<h1>Kredietoverzicht</h1>
<div class="org">${d.bank} · Kredietnummer 000-0000000-00</div>
<div class="meta">Kredietnemer: ${d.name}</div>
<table>
  <tr><th>Omschrijving</th><th class="right">Bedrag</th></tr>
  <tr><td>Openstaand saldo</td><td class="right">${money(d.balance)}</td></tr>
  <tr class="total"><td>Maandelijkse aflossing</td><td class="right">${money(d.instalment)}</td></tr>
</table>
<div class="stamp">Fictief document voor testdoeleinden.</div>`;

const compromis = (d) => `
<h1>Compromis van verkoop</h1>
<div class="org">Notariskantoor ${d.notary}</div>
<div class="meta">
  Verkoper: ${d.seller}<br>
  Koper: ${d.buyer}<br>
  Datum akte: ${d.deed}
</div>
<table>
  <tr class="total"><td>Verkoopprijs</td><td class="right">${money(d.price)}</td></tr>
</table>
<div class="stamp">Fictief document voor testdoeleinden.</div>`;

const DOCS = [
  ...[
    { id: 'payslip-01', employer: 'Vandenberghe NV', employee: 'Jan Peeters', period: '2026-03', gross: 4800, rsz: 627, tax: 973, net: 3200 },
    { id: 'payslip-02', employer: 'De Smet BVBA', employee: 'Sofie Maes', period: '2026-02', gross: 3600, rsz: 470, tax: 680, net: 2450 },
    { id: 'payslip-03', employer: 'Logistiek Antwerpen NV', employee: 'Karim Blondeel', period: '2026-01', gross: 6200, rsz: 810, tax: 1490, net: 3900 },
    { id: 'payslip-04', employer: 'Zorggroep Leuven vzw', employee: 'Els Verhoeven', period: '2026-03', gross: 3100, rsz: 405, tax: 520, net: 2175 },
  ].map((d) => ({ ...d, type: 'PAYSLIPS', html: payslip(d) })),
  ...[
    { id: 'tax-01', name: 'Jan Peeters', year: 2025, gross: 57600, net: 48000 },
    { id: 'tax-02', name: 'Sofie Maes', year: 2025, gross: 43200, net: 35400 },
    { id: 'tax-03', name: 'Karim Blondeel', year: 2024, gross: 74400, net: 61200 },
  ].map((d) => ({ ...d, type: 'TAX_ASSESSMENT', html: taxAssessment(d) })),
  ...[
    { id: 'accountant-01', firm: 'Boekhoudkantoor Dierckx', name: 'Lieve Goossens', year: 2025, turnover: 96000, net: 50000 },
    { id: 'accountant-02', firm: 'Fiduciaire Charleroi SPRL', name: 'Marc Dubois', year: 2024, turnover: 71000, net: 38400 },
    { id: 'accountant-03', firm: 'Accountancy Gent BV', name: 'Ann Willems', year: 2025, turnover: 120000, net: 66000 },
  ].map((d) => ({ ...d, type: 'ACCOUNTANT_STATEMENT', html: accountant(d) })),
  ...[
    { id: 'employer-01', employer: 'Vandenberghe NV', employee: 'Jan Peeters', contract: 'Onbepaalde duur', start: '06/01/2020', gross: 57600 },
    { id: 'employer-02', employer: 'De Smet BVBA', employee: 'Sofie Maes', contract: 'Bepaalde duur', start: '01/09/2024', gross: 43200 },
    { id: 'employer-03', employer: 'Logistiek Antwerpen NV', employee: 'Karim Blondeel', contract: 'Onbepaalde duur', start: '15/03/2018', gross: 74400 },
  ].map((d) => ({ ...d, type: 'EMPLOYER_STATEMENT', html: employer(d) })),
  ...[
    { id: 'loan-01', bank: 'Argenta', name: 'Jan Peeters', balance: 12000, instalment: 250 },
    { id: 'loan-02', bank: 'Belfius', name: 'Sofie Maes', balance: 4800, instalment: 145 },
    { id: 'loan-03', bank: 'KBC', name: 'Karim Blondeel', balance: 26500, instalment: 410 },
  ].map((d) => ({ ...d, type: 'EXISTING_LOAN_STATEMENTS', html: loan(d) })),
  ...[
    { id: 'compromis-01', notary: 'Claes & Partners', seller: 'Familie Janssens', buyer: 'Jan Peeters', deed: '01/06/2026', price: 300000 },
    { id: 'compromis-02', notary: 'Etude Lambert', seller: 'M. Rousseau', buyer: 'Sofie Maes', deed: '15/07/2026', price: 245000 },
    { id: 'compromis-03', notary: 'Notariaat Brugge', seller: 'Bouwbedrijf Devos NV', buyer: 'Karim Blondeel', deed: '03/09/2026', price: 412500 },
    { id: 'compromis-04', notary: 'Claes & Partners', seller: 'Mevr. Dewaele', buyer: 'Els Verhoeven', deed: '22/05/2026', price: 189000 },
  ].map((d) => ({ ...d, type: 'PURCHASE_AGREEMENT', html: compromis(d) })),
];

const browser = await chromium.launch();
const page = await browser.newPage();
for (const doc of DOCS) {
  await page.setContent(`<style>${css}</style>${doc.html}`, { waitUntil: 'load' });
  // Both formats on purpose. PDF is what a borrower actually uploads and is
  // what the corpus is for; PNG additionally lets the fixtures be rendered and
  // inspected without poppler, which is a container dependency rather than a
  // developer one.
  await page.pdf({ path: join(out, `${doc.id}.pdf`), format: 'A4', printBackground: true });
  await page.setViewportSize({ width: 900, height: 1160 });
  await page.screenshot({ path: join(out, `${doc.id}.png`), fullPage: true });
}
await browser.close();
console.log(`rendered ${DOCS.length} documents into ${out}`);
