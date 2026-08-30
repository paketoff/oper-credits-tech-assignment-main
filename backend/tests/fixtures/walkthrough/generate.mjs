import { chromium } from '/Users/paketoff/Desktop/oper-credits-tech-assignment-main/frontend/node_modules/playwright/index.mjs';
import { writeFileSync } from 'node:fs';

const OUT = '/Users/paketoff/Desktop/oper-credits-tech-assignment-main/backend/tests/fixtures/walkthrough';
const CSS = `body{font:14px/1.55 -apple-system,Segoe UI,Roboto,sans-serif;color:#111;margin:56px 60px}
h1{font-size:20px;margin:0 0 4px}.sub{color:#555;margin:0 0 26px;font-size:13px}
table{width:100%;border-collapse:collapse;margin:18px 0}
th{text-align:left;background:#f2f4f4;padding:8px 10px;font-size:13px}
td{padding:8px 10px;border-bottom:1px solid #e3e6e6}
td.r,th.r{text-align:right}.tot td{font-weight:700;border-bottom:none;border-top:2px solid #111}
.meta{color:#555;font-size:13px;margin:2px 0}
.foot{margin-top:40px;padding-top:12px;border-top:1px solid #e3e6e6;color:#777;font-size:11px}
.stub{margin:26px 0;padding:22px;border:2px dashed #bbb;color:#666;text-align:center;font-size:13px}`;

const FOOT = '<div class="foot">Dit is een fictief document, aangemaakt voor testdoeleinden. Alle gegevens zijn verzonnen.</div>';

const docs = [
  ['1-identity-document', `<h1>Identiteitskaart — testdocument</h1>
   <p class="sub">Bewijs van identiteit · plaatshouder voor de checklist</p>
   <p class="meta">Naam: Jan Peeters</p><p class="meta">Geboortedatum: 12.04.1990</p>
   <p class="meta">Rijksregisternummer: 00.00.00-000.00</p><p class="meta">Geldig tot: 31.12.2032</p>
   <div class="stub">Uit dit documenttype worden bewust geen gegevens uitgelezen.<br>
   Een rijksregisternummer is een andere GDPR-verbintenis dan een loonbedrag.</div>`],

  ['2-bank-statements', `<h1>Rekeninguittreksel — 2026/03</h1>
   <p class="sub">Belfius Bank NV · rekening BE00 0000 0000 0000</p>
   <p class="meta">Rekeninghouder: Jan Peeters</p><p class="meta">Periode: 01.03.2026 — 31.03.2026</p>
   <table><tr><th>Datum</th><th>Omschrijving</th><th class="r">Bedrag</th></tr>
   <tr><td>02.03</td><td>Huur</td><td class="r">- € 850,00</td></tr>
   <tr><td>05.03</td><td>Loon Vandenberghe NV</td><td class="r">+ € 2.500,00</td></tr>
   <tr><td>11.03</td><td>Supermarkt</td><td class="r">- € 214,30</td></tr>
   <tr><td>20.03</td><td>Energie</td><td class="r">- € 118,45</td></tr>
   <tr class="tot"><td colspan="2">Eindsaldo</td><td class="r">€ 4.812,25</td></tr></table>`],

  ['3-purchase-agreement', `<h1>Compromis van verkoop</h1>
   <p class="sub">Onderhandse verkoopovereenkomst · woning</p>
   <p class="meta">Verkoper: Els Vandevelde</p><p class="meta">Koper: Jan Peeters</p>
   <p class="meta">Ligging: Vlaanderen · bestaande woning</p>
   <table><tr><th>Omschrijving</th><th class="r">Bedrag</th></tr>
   <tr><td>Overeengekomen verkoopprijs</td><td class="r">€ 200.000,00</td></tr>
   <tr><td>Voorschot bij ondertekening (10%)</td><td class="r">€ 20.000,00</td></tr>
   <tr class="tot"><td>Saldo bij authentieke akte</td><td class="r">€ 180.000,00</td></tr></table>
   <p class="meta">Verlijden van de akte: uiterlijk 30.11.2026</p>`],

  ['4-recent-payslips', `<h1>Loonfiche — 2026-03</h1>
   <p class="sub">Vandenberghe NV · ondernemingsnummer 0000.000.000</p>
   <p class="meta">Werknemer: Jan Peeters</p><p class="meta">Functie: bediende · voltijds</p>
   <table><tr><th>Omschrijving</th><th class="r">Bedrag</th></tr>
   <tr><td>Brutoloon</td><td class="r">€ 3.750,00</td></tr>
   <tr><td>RSZ-bijdrage</td><td class="r">- € 490,13</td></tr>
   <tr><td>Bedrijfsvoorheffing</td><td class="r">- € 759,87</td></tr>
   <tr class="tot"><td>Netto te betalen</td><td class="r">€ 2.500,00</td></tr></table>`],

  ['5-employer-statement', `<h1>Werkgeversattest</h1>
   <p class="sub">Vandenberghe NV · ondernemingsnummer 0000.000.000</p>
   <p>Hierbij bevestigen wij dat Jan Peeters bij ons in dienst is als bediende.</p>
   <table><tr><th>Omschrijving</th><th class="r">Gegeven</th></tr>
   <tr><td>Type contract</td><td class="r">Onbepaalde duur</td></tr>
   <tr><td>Datum indiensttreding</td><td class="r">01.09.2021</td></tr>
   <tr><td>Arbeidsregime</td><td class="r">Voltijds (38u/week)</td></tr>
   <tr class="tot"><td>Bruto jaarloon</td><td class="r">€ 45.000,00</td></tr></table>
   <p class="meta">De werknemer bevindt zich niet in opzegperiode.</p>`],

  ['6-energy-performance-certificate', `<h1>Energieprestatiecertificaat</h1>
   <p class="sub">EPC voor een bestaande woning · Vlaams Energie- en Klimaatagentschap</p>
   <p class="meta">Certificaatnummer: 00000000-0000-0000</p><p class="meta">Datum opmaak: 14.01.2026</p>
   <table><tr><th>Omschrijving</th><th class="r">Waarde</th></tr>
   <tr><td>Beschermd volume</td><td class="r">412 m³</td></tr>
   <tr><td>Bruikbare vloeroppervlakte</td><td class="r">148 m²</td></tr>
   <tr class="tot"><td>Energiescore · label C</td><td class="r">210 kWh/m²</td></tr></table>
   <p class="meta">Geldig tot 14.01.2036.</p>`],

  ['7-existing-loan-statement', `<h1>Kredietoverzicht</h1>
   <p class="sub">AXA Bank Belgium NV · autolening</p>
   <p class="meta">Kredietnemer: Jan Peeters</p><p class="meta">Dossiernummer: 0000-0000-0000</p>
   <table><tr><th>Omschrijving</th><th class="r">Bedrag</th></tr>
   <tr><td>Oorspronkelijk kredietbedrag</td><td class="r">€ 18.000,00</td></tr>
   <tr><td>Openstaand saldo</td><td class="r">€ 12.000,00</td></tr>
   <tr><td>Einddatum</td><td class="r">31.10.2030</td></tr>
   <tr class="tot"><td>Maandelijkse aflossing</td><td class="r">€ 250,00</td></tr></table>`],
];

const browser = await chromium.launch();
const page = await browser.newPage();
for (const [name, body] of docs) {
  await page.setContent(`<style>${CSS}</style>${body}${FOOT}`);
  await page.pdf({ path: `${OUT}/${name}.pdf`, format: 'A4', printBackground: true });
  console.log(name);
}
await browser.close();
