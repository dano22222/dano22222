# Response to Part 2 feedback

| Feedback | Part 3 response | Verification |
|---|---|---|
| Abdirahman: add a date selector to Reservoir Data | One inclusive interval filters overview sparklines, the detailed dataset and its CSV export together. | Boundary test includes all of the end date; Streamlit test selects January 2024 and checks both tables. |
| Yue Yang: improve crowded plots | A single area and variable are the defaults. Optional comparisons retain prior functionality. Separate panels keep different units apart; axes name units explicitly. New figures use clear labels, limits and contrasting anomaly markers. | Runtime tests cover single and multiple areas; notebook figures and local app inspected. |
| Abdirahman: organise notebooks and reports | notebooks/ holds historical copies and Part 3; reports/ holds the new outputs and historical PDF copies in part1/ and part2/. Root originals and videos remain accessible. | File inventory and Git history; backups retained. |
| Abdirahman: add README | README.md describes all project parts, technologies, structure, installation, app startup, data preparation, testing, sources and original links. | Instructions exercised with a separate environment in the original project. |
| Retain good AI documentation and development log | AI assistance is described transparently. The technical development log is within the required 300–500 words and does not invent student experiences. | Word count checked; both sections included in the notebook and PDF. |
| Retain Spark, Cassandra and MongoDB work | Historical notebooks and the electricity page are preserved. No Spark/Cassandra reprocessing or database writes are needed for Part 3. MongoDB still reads the existing collection. | Read-only connection confirmed 114528 documents; electricity page rendered with actual records and also with test fixtures. |
| Retain secure secrets handling | Existing .env and Streamlit secrets logic remains. Added an explicit CA bundle for certificate verification; TLS remains enabled. | Real read-only MongoDB connection succeeded. No secrets added to version control. |
| Retain direct NVE access and downloads | The existing cached NVE API loader remains; old export functionality is retained and the Data page also exports the selected interval. | Real NVE retrieval, date/export tests and local browser checks. |
| Kristian: keep the same app URL | The existing app.py deployment entry point and original Streamlit URL are retained. No new Streamlit app is created. | Final deployment check recorded in the delivery status. |
| Kristian: use branches and merge into main | Part 2 merge 8dbf70b was verified on origin/main. Part 3 is developed on part3-development and must have its own visible merge commit. | Final Git history and remote references recorded in the delivery status. |

## Selector scope

The area type and area are shared across reservoir and weather pages. Reservoir Data's date interval and Reservoir Plots' year/months are local controls. STL and the spectrogram deliberately use the selected area's complete multi-year weekly history. Weather has a local year selector and uses a complete year for robust SPC statistics. The electricity page retains its independent connection, year and month controls.
