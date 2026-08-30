# Walkthrough corpus — one document per checklist row

For clicking through the product by hand, not for the test suite. The suite's
corpus is `../documents/`, which holds several variants per extractable type and
is checked against `../expected.yaml`; this holds **exactly one file per row**,
named after the row it belongs in, so there is nothing to look up.

The figures across these seven documents are one coherent borrower — Jan
Peeters, employed, buying a €200 000 existing house in Flanders on €2 500 net a
month. Everything is invented, every reference number is a run of zeroes, and
each page says so in its footer.

| File | Checklist row | What the classifier should do |
|---|---|---|
| `1-identity-document.pdf` | Identity document | Confirm the type. **Nothing is extracted** — a national register number is a different GDPR commitment from a salary figure (T56), so this row never proposes anything. |
| `2-bank-statements.pdf` | Bank statements | Confirm the type. Nothing extracted, same reason. |
| `3-purchase-agreement.pdf` | Purchase agreement | Confirm the type. Reads the €200 000 price but proposes nothing: the assessment reads income and existing credit, and neither is a purchase price. |
| `4-recent-payslips.pdf` | Recent payslips | Confirm, and **propose €2 500,00** as net monthly income. |
| `5-employer-statement.pdf` | Employer statement | Confirm the type. Proposes nothing: the €45 000 on it is *gross*, and converting gross to net would be inventing a tax model. |
| `6-energy-performance-certificate.pdf` | Energy performance certificate | Confirm the type. Carries no figure any calculation reads. |
| `7-existing-loan-statement.pdf` | Existing loan statements | Confirm, and **propose €250,00** as existing monthly credit. Only appears on the checklist when the borrower ticked an existing credit. |

Proposals need `AI_CLASSIFICATION_ENABLED=true` and a key. With the flag off
every row still closes on upload and the borrower types the two figures
themselves — that is the base case, not a fallback (`AI-039`).

**Worth trying deliberately:** put `4-recent-payslips.pdf` into *Bank
statements*. The row still closes — the borrower is the authority on what they
uploaded — but the classifier says it looks like a payslip, and its €2 500 is
discarded rather than proposed. Figures read off a document that turned out to
be something else describe the wrong document (`AI-003`, `AI-006`).

Regenerate with `node generate.mjs` (needs the frontend's Playwright install).
