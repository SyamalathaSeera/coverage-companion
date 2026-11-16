# GoMask synthetic records

The local app includes 8 transactions for 8 synthetic patients from the public
[Eligibility and Benefits Verification preview](https://gomask.ai/marketplace/datasets/eligibility-and-benefits-verification),
retrieved November 16, 2026. The live public HTML exposed 8 rows; the indexed page
previously showed 5. This is not the full advertised 110-record dataset.

The three original demo members remain available. Select a GoMask entry and expand
**View selected record** to inspect its fields. Ask about its deductible, copay,
coinsurance, recorded status, or prior authorization. Patient names and plan names
are not supplied, so the app uses patient IDs and service descriptions.

Transactions are selected individually using `GM-<transaction_id>`. A patient may
have several services or transactions in a full export; those must not overwrite
each other. Copays are service-specific and deductible totals are not assumed to
be annual. Status always refers to the historical transaction. Zero values do not
establish free coverage, especially for denied or terminated records.

## Import the full export

The advertised CSV download redirects to GoMask sign-in. On inspection, the site
offered a free sample and priced the full export at $1.99. No account was created
and no purchase was made. Obtain an authorized CSV or JSON export from GoMask, then:

```powershell
.\.venv\Scripts\python.exe -m scripts.import_gomask path\to\export.csv
```

Restart the app. The selector loads all imported transactions automatically.
The importer checks required columns, numeric ranges, transaction IDs, and duplicate
transactions before replacing the GoMask data. Repeated patient IDs are supported.
Only synthetic exports belong in this demo.

GoMask data is stored separately in `backend/data/gomask.json`, excluded from Git.
Original exports should be placed in the ignored `private-data` folder.
GoMask links its [EULA](https://gomask.ai/eula) as the dataset license; this is not
a verified open-data license. Confirm permission for public redistribution before
including the data in a published repository or hosted app.
